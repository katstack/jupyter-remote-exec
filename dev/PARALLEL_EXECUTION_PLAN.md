# 병렬 실행 아키텍처 계획

터미널과 Jupyter 환경 모두에서 동작하는 병렬 실행 기능 설계

---

## 1. 환경 감지 전략

### 감지 방법
```python
def detect_environment() -> str:
    """Jupyter인지 터미널인지 감지"""
    try:
        shell = get_ipython().__class__.__name__
        if shell in ['ZMQInteractiveShell', 'Shell']:  # Jupyter
            return 'jupyter'
    except NameError:
        pass
    return 'terminal'
```

**폴백:** 감지 실패시 터미널 모드로 기본 설정 (더 안전함)

---

## 2. 모듈 구조

```
src/jupyter_remote_exec/
├── core.py              # 메인 API (exec_on_remote, shell_on_remote)
├── ws_client.py         # WebSocket 통신 (변경 없음)
├── msg_models.py        # 메시지 빌더 (변경 없음)
├── parallel/
│   ├── __init__.py
│   ├── base.py          # 렌더러 추상 베이스 클래스
│   ├── terminal.py      # Rich 기반 터미널 렌더러
│   ├── jupyter.py       # ipywidgets 기반 Jupyter 렌더러
│   └── executor.py      # 병렬 실행 오케스트레이터
└── utils/
    ├── __init__.py
    └── config.py        # 설정 관리
```

---

## 3. 공통 추상화

### 베이스 렌더러 인터페이스

```python
class BaseRenderer(ABC):
    @abstractmethod
    def initialize(self, remotes: list[str]) -> None:
        """리모트들을 위한 UI 컴포넌트 설정"""
        pass

    @abstractmethod
    def update(self, remote: str, content: str, status: str) -> None:
        """특정 리모트의 디스플레이 업데이트"""
        pass

    @abstractmethod
    def finalize(self, buffers: dict) -> None:
        """정리 및 최종 결과 표시"""
        pass

    @abstractmethod
    def show_logs(self, buffers: dict) -> None:
        """접을 수 있는/완전한 로그 표시"""
        pass
```

### Executor (환경 독립적)

역할:
- 스레딩 관리
- StringIO 버퍼에 출력 수집
- 적절한 렌더러에 렌더링 위임
- 로그 파일 저장 처리

---

## 4. API 디자인

### 현재 API (단일 리모트)
```python
exec_on_remote(remote_name, code, file=None)
shell_on_remote(remote_name, command, file=None)
```

### 새로운 병렬 API

**옵션 A: 별도 함수 (추천)**
```python
exec_on_remotes(
    remotes: list[str],
    code: str,
    parallel: bool = True,
    columns: int = None,  # None이면 자동 감지
    save_logs: bool = True,
    log_dir: str = "./logs",
    refresh_rate: float = 0.3  # 초
) -> dict[str, StringIO]

shell_on_remotes(
    remotes: list[str],
    command: str,
    **kwargs  # exec_on_remotes와 동일
) -> dict[str, StringIO]
```

**옵션 B: 기존 함수 확장 (하위 호환성 유지)**
```python
exec_on_remote(
    remote_name: str | list[str],  # 둘 다 받음!
    code: str,
    file: TextIO = None,  # 리모트 리스트면 무시
    parallel: bool = True,
    **parallel_options
) -> StringIO | dict[str, StringIO]
```

**결정:** 옵션 A - 의도가 더 명확하고 유지보수 쉬움

---

## 5. 기능 매트릭스

| 기능 | 터미널 (Rich) | Jupyter (ipywidgets) | 비고 |
|------|--------------|---------------------|------|
| 실시간 업데이트 | ✅ 됨 | ✅ 됨 | 둘 다 부드럽게 동작 |
| 그리드 레이아웃 | ✅ 3열 자동 | ✅ 세로 스택 | Jupyter: 가로 공간 제한적 |
| 색상 코딩 | ✅ ANSI 색상 | ✅ HTML 색상 | 구현 방식 다름 |
| 진행 표시 | ✅ Live 새로고침 | ✅ HTML 업데이트 | 둘 다 부드러움 |
| 로그 접기 | ❌ 해당없음 | ✅ `<details>` | 터미널: 스크롤 버퍼 대신 |
| 전체 로그 출력 | ✅ Live 이후 | ✅ 접을 수 있음 | 둘 다 지원 |
| 파일 저장 | ✅ 됨 | ✅ 됨 | 동일한 동작 |
| 인터랙티브 TTY 필요 | ✅ 필요 | ❌ 불필요 | 터미널은 실제 TTY 필요 |

---

## 6. 의존성

### 코어 (이미 있음)
- `websocket-client`
- 표준 라이브러리: `threading`, `io`, `pathlib`, `datetime`

### 선택적 (자동 설치 또는 우아한 degradation)
- `rich` - 터미널 렌더링 (없으면 단순 출력으로 폴백)
- `ipywidgets` - Jupyter 렌더링 (Jupyter인데 없으면 도움말 메시지와 함께 에러)

### 설치 그룹
```toml
[project.optional-dependencies]
terminal = ["rich>=13.0.0"]
jupyter = ["ipywidgets>=8.0.0"]
all = ["rich>=13.0.0", "ipywidgets>=8.0.0"]
```

---

## 7. 설정 옵션

### 사용자 설정
```python
@dataclass
class ParallelConfig:
    # 레이아웃
    columns: int | None = None  # None이면 자동 감지
    max_lines_live: int = 10    # 실행 중 마지막 N줄만 표시

    # 성능
    refresh_rate: float = 0.3   # 업데이트 간격 (초)

    # 로깅
    save_logs: bool = True
    log_dir: str = "./logs"
    timestamp_format: str = "%Y%m%d_%H%M%S"

    # 디스플레이
    show_line_count: bool = True
    color_scheme: dict = field(default_factory=lambda: {
        'waiting': 'yellow',
        'running': 'cyan',
        'completed': 'green',
        'error': 'red'
    })
```

### 자동 감지 로직
```python
def auto_detect_columns(n_remotes: int, env: str) -> int:
    if env == 'jupyter':
        return 1  # Jupyter에서는 세로 스택

    # 터미널: 그리드 레이아웃
    if n_remotes <= 3:
        return 1
    elif n_remotes <= 6:
        return 2
    else:
        return 3  # 가독성 위해 최대 3열
```

---

## 8. 실행 흐름

```
사용자가 exec_on_remotes(remotes, code) 호출
    ↓
환경 감지 (터미널 vs jupyter)
    ↓
적절한 렌더러 생성 (TerminalRenderer or JupyterRenderer)
    ↓
리모트 리스트로 렌더러 초기화
    ↓
각 리모트별 스레드 시작
    ↓
업데이트 루프:
    - 버퍼에서 출력 수집
    - 각 리모트별 renderer.update() 호출
    - Sleep (refresh_rate)
    ↓
모든 스레드 완료 대기
    ↓
최종 표시를 위해 renderer.finalize() 호출
    ↓
파일에 로그 저장 (활성화된 경우)
    ↓
버퍼 dict 반환
```

---

## 9. 하위 호환성

### 전략
- 기존 `exec_on_remote()`, `shell_on_remote()` 변경 없이 유지
- 병렬용 새 함수 `exec_on_remotes()`, `shell_on_remotes()`
- 기존 코드에 breaking change 없음

### 마이그레이션 경로
```python
# 기존 방식 (여전히 동작)
exec_on_remote('us-east-1', code, file=sys.stdout)

# 새 방식 (병렬)
exec_on_remotes(['us-east-1', 'eu-west-1'], code)
```

---

## 10. 에러 처리

### 리모트별 에러
- 하나 실패해도 다른 리모트들 멈추지 않음
- 실패한 리모트는 빨간색으로 에러 메시지와 함께 표시
- 저장된 로그에 에러 포함
- 부분 결과 반환

### 렌더러 에러
- 단순 print 기반 출력으로 우아하게 폴백
- 누락된 의존성에 대한 경고 로그
- 실행은 계속 (데이터 수집은 여전히 동작)

---

## 11. 구현 단계

### Phase 1: 코어 추상화
- `BaseRenderer` 추상 클래스
- `ParallelExecutor` 오케스트레이터
- 환경 감지

### Phase 2: 터미널 렌더러
- Rich 사용하는 `TerminalRenderer`
- 그리드 레이아웃 로직
- Live 업데이트

### Phase 3: Jupyter 렌더러
- ipywidgets 사용하는 `JupyterRenderer`
- HTML 기반 부드러운 업데이트
- 접을 수 있는 로그

### Phase 4: 통합
- `exec_on_remotes()`, `shell_on_remotes()` API
- 설정 관리
- 파일 로깅

### Phase 5: 마무리
- 에러 처리
- 양쪽 환경 테스트
- 문서화

---

## 12. 테스트 전략

### 유닛 테스트
- WebSocket 연결 모킹
- 각 렌더러 독립적으로 테스트
- Executor 로직 테스트

### 통합 테스트
- 실제 Jupyter 커널 연결 사용
- 터미널/Jupyter 양쪽에서 테스트
- 로그 파일 생성 검증

### 테스트 파일
```
tests/
├── test_parallel_executor.py
├── test_terminal_renderer.py
├── test_jupyter_renderer.py
└── notebooks/
    └── test_parallel_jupyter.ipynb
```

---

## 요약

### 핵심 설계 결정

1. **분리된 렌더러** - 터미널/Jupyter는 구현은 다르지만 동일한 인터페이스
2. **새 API 함수** - 기존 함수 오버로딩 대신 `exec_on_remotes()`
3. **자동 감지** - 환경과 레이아웃 열 자동 감지
4. **선택적 의존성** - Rich/ipywidgets는 필요할 때만 설치
5. **파일 로깅** - 환경 무관하게 항상 로그 저장
6. **Breaking change 없음** - 기존 코드 계속 동작

### 참고 PoC 파일
- `dev/rich_parallel_poc.py` - 터미널 렌더러 참고
- `dev/grid_layout_poc.py` - 그리드 레이아웃 참고
- `dev/logs_after_live.py` - 로그 저장 참고
- `dev/test_jupyter_smooth.ipynb` - Jupyter 렌더러 참고

---

## 다음 단계

1. `BaseRenderer`와 `ParallelExecutor` 구현
2. `rich_parallel_poc.py` 기반으로 `TerminalRenderer` 생성
3. `test_jupyter_smooth.ipynb` 기반으로 `JupyterRenderer` 생성
4. 새 API 함수에 모두 연결
5. 테스트 및 문서 추가
