# Jupyter Region Magic

분산 컴퓨팅 환경을 위한 IPython 매직 확장입니다. 여러 원격 Jupyter 서버(리전)에서 동일한 코드를 실행하거나 특정 리전에서만 코드를 실행할 수 있습니다.

## 주요 기능

- ✅ 여러 리전에서 동시에 코드 실행
- ✅ 특정 리전 선택 실행
- ✅ 함수형 프로그래밍 스타일 지원
- ✅ 자동 커널 관리
- ✅ WebSocket 기반 원격 실행

## 설치

### 방법 1: IPython 확장 디렉토리에 복사 (권장)

```bash
mkdir -p ~/.ipython/extensions
cp region_magic.py ~/.ipython/extensions/
```

### 방법 2: 현재 디렉토리에서 사용

```python
# Jupyter Notebook에서
%load_ext region_magic
```

## 설정

`region_magic.py` 파일을 열어 리전 정보를 설정하세요:

```python
REGION_CONFIG = {
    'us-east': {'host': 'east-server.example.com', 'port': 8888},
    'us-west': {'host': 'west-server.example.com', 'port': 8888},
    'eu-central': {'host': 'eu-server.example.com', 'port': 8888},
    'asia-pacific': {'host': 'asia-server.example.com', 'port': 8888},
}

SHARED_TOKEN = 'your_jupyter_token_here'
```

## 사용법

### 1. 확장 로드

```python
%load_ext region_magic
```

### 2. 기본 사용법

#### 모든 리전에서 실행

```python
def my_task():
    import sys
    print(f"Python: {sys.executable}")

exec_on_region(my_task)
```

출력:
```
==================================================
Region: us-east
==================================================
Python: /usr/bin/python3

==================================================
Region: us-west
==================================================
Python: /usr/bin/python3

==================================================
Region: eu-central
==================================================
Python: /usr/bin/python3

==================================================
Region: asia-pacific
==================================================
Python: /usr/bin/python3
```

#### 특정 리전에서만 실행

```python
def check_disk():
    import os
    print(os.getcwd())

# 단일 리전
exec_on_region(check_disk, 'us-east')

# 여러 리전
exec_on_region(check_disk, ['us-east', 'us-west'])
```

#### 동적으로 리전 선택

```python
def my_task():
    import sys
    print(sys.version)

# 리전 목록 가져오기
regions = get_regions()
print(f"Available: {regions}")

# 선택적으로 실행
selected = ['us-east', 'eu-central']
exec_on_region(my_task, selected)
```

### 3. 매직 커맨드 사용

#### 리전 상태 확인

```python
%regions
```

출력:
```
Available regions:
  🟢 ACTIVE us-east: localhost:8889 (kernel: c900984c...)
  🔵 ready us-west: localhost:8890 (kernel: d19f0a2b...)
  ⚪ not initialized eu-central: localhost:8891
  ⚪ not initialized asia-pacific: localhost:8892

🟢 ACTIVE: LOCAL
```

#### 실행 컨텍스트 전환 (선택적 기능)

```python
%region us-east
# 이후 모든 셀은 us-east 리전에서 실행됨

import sys
print(sys.executable)

%region local  # 다시 로컬로
```

## 사용 예시

### 예시 1: 서버 정보 수집

```python
def collect_info():
    import sys
    import os
    import socket
    
    print(f"Hostname: {socket.gethostname()}")
    print(f"Python: {sys.version}")
    print(f"CWD: {os.getcwd()}")

exec_on_region(collect_info)
```

### 예시 2: 분산 데이터 처리

```python
def process_data():
    import pandas as pd
    
    # 각 리전에서 로컬 데이터 처리
    df = pd.read_csv('local_data.csv')
    result = df.groupby('category').sum()
    print(result)

exec_on_region(process_data, ['us-east', 'us-west', 'eu-central'])
```

### 예시 3: 조건부 실행

```python
def my_task():
    import time
    print(f"Task started at {time.time()}")
    time.sleep(1)
    print("Task completed")

# 특정 조건에 따라 실행할 리전 선택
high_priority_regions = ['us-east', 'eu-central']
exec_on_region(my_task, high_priority_regions)
```

## API 레퍼런스

### 함수

#### `exec_on_region(func, regions=None)`

지정된 리전(들)에서 함수를 실행합니다.

**Parameters:**
- `func` (callable): 실행할 Python 함수
- `regions` (str | list | None): 실행할 리전 지정
  - `None`: 모든 리전
  - `'us-east'`: 단일 리전
  - `['us-east', 'us-west']`: 여러 리전

**Returns:** None (결과는 stdout으로 출력)

#### `get_regions()`

사용 가능한 리전 목록을 반환합니다.

**Returns:** `list` - 리전 이름 리스트

### 매직 커맨드

#### `%regions`

모든 리전의 상태를 출력합니다.

#### `%region <name>`

현재 실행 컨텍스트를 특정 리전으로 전환합니다.

**Parameters:**
- `<name>`: 리전 이름 또는 'local'

## 아키텍처

```
┌─────────────────┐
│  Control Node   │
│  (Jupyter Lab)  │
└────────┬────────┘
         │
         ├─ WebSocket ─> ┌──────────────┐
         │                │ us-east      │
         │                │ (Kernel)     │
         │                └──────────────┘
         │
         ├─ WebSocket ─> ┌──────────────┐
         │                │ us-west      │
         │                │ (Kernel)     │
         │                └──────────────┘
         │
         ├─ WebSocket ─> ┌──────────────┐
         │                │ eu-central   │
         │                │ (Kernel)     │
         │                └──────────────┘
         │
         └─ WebSocket ─> ┌──────────────┐
                          │ asia-pacific │
                          │ (Kernel)     │
                          └──────────────┘
```

### 통신 프로토콜

1. **커널 생성**: HTTP POST 요청으로 각 리전에 Python 커널 생성
2. **코드 실행**: WebSocket을 통해 Jupyter 메시지 프로토콜로 코드 전송
3. **결과 수신**: IOPub 채널을 통해 stdout/stderr 수신

## 제약사항

- 각 리전의 Jupyter 서버는 동일한 인증 토큰을 사용해야 합니다
- 함수는 `inspect.getsource()`로 추출 가능해야 합니다 (람다 함수는 제한적)
- 네트워크 지연에 따라 실행 시간이 달라질 수 있습니다

## 트러블슈팅

### 문제: "Failed to create kernel"

**원인:** 리전 서버에 연결할 수 없거나 인증 실패

**해결:**
1. 리전 서버가 실행 중인지 확인
2. `SHARED_TOKEN`이 올바른지 확인
3. 네트워크 연결 확인

### 문제: "IndentationError" 또는 문법 오류

**원인:** 함수 소스 코드 추출 실패

**해결:**
- 함수를 노트북 셀에 직접 정의하세요
- 클래스 메서드나 중첩 함수는 제한적으로 지원됩니다

### 문제: 출력이 두 번 나타남

**원인:** IPython의 input transformer가 두 번 호출됨

**해결:**
- 정상 동작입니다. 함수형 API(`exec_on_region`)를 사용하세요

## 개발 정보

- **Python**: 3.8+
- **Dependencies**: 
  - `IPython`
  - `websocket-client`
  - `requests`
  - `jupyter-server`

## 라이선스

MIT License

## 기여

이슈 및 풀 리퀘스트를 환영합니다!

## 버전 히스토리

### v1.0.0 (2025-10-29)
- 초기 릴리스
- 기본 리전 실행 기능
- 함수형 API 지원
- 자동 커널 관리