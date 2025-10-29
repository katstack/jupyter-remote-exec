# jupyter-remote-exec

이제 라이브러리 API + 선택적 IPython 매직 래퍼 구조입니다. 노트북에서는 `%load_ext`로 편하게 쓰고, 스크립트/테스트/CLI에서는 일반 파이썬 모듈처럼 `jupyter_remote_exec`를 임포트해 사용하세요.

## 주요 기능

- ✅ 여러 리모트에서 코드 실행 (동시에/선택적으로)
- ✅ 함수(소스) 전송 후 원격 실행
- ✅ 설정 파일/환경변수/런타임 구성 지원
- ✅ 자동 커널 생성 및 캐싱
- ✅ HTTP(S)/WS(S) 및 인증서 검증 옵션

## 사용 방법 요약

- 라이브러리 API (권장, 어디서나 사용):

```python
from jupyter_remote_exec import shell_on_remote, get_remotes

print(get_remotes())

# 모든 리모트에서 코드 셀 실행
shell_on_remote("""
import sys
print(sys.version)
""")

# 특정 리모트에서만 실행
shell_on_remote("""
print('Hello from us-east')
""", 'us-east')
```

- IPython 매직(선택): 노트북에서 편의용 래퍼

```ipython
%load_ext jupyter_remote_exec_magic_wrapper
# 로드되면 아래 함수들이 전역 네임스페이스에 바인딩됩니다
# exec_on_remote, shell_on_remote, get_remotes
```

## 설치

### 방법 1: IPython 확장 디렉토리에 복사 (노트북에서 매직 사용 시)

```bash
mkdir -p ~/.ipython/extensions
cp jupyter_remote_exec_magic_wrapper.py ~/.ipython/extensions/jupyter_remote_exec_magic_wrapper.py
```

### 방법 2: 현재 디렉토리에서 라이브러리로 사용

```python
from jupyter_remote_exec import shell_on_remote
```

## 설정

설정은 파일/환경변수/런타임 코드로 구성할 수 있습니다. 레거시 상수(`REMOTE_CONFIG`, `SHARED_TOKEN`)는 더 이상 사용하지 않습니다.

### 1) pyproject.toml

프로젝트 루트의 `pyproject.toml`에 다음 섹션을 추가하세요.

```toml
[tool.jupyter_remote_exec]
shared_token = "your_shared_token"   # 선택사항

[tool.jupyter_remote_exec.remotes.us-east]
host = "east-server.example.com"
port = 8888
https = true            # 선택사항, 기본 false
verify = "/path/to/ca.pem"  # true/false 또는 CA 번들 경로

[tool.jupyter_remote_exec.remotes.us-west]
host = "west-server.example.com"
port = 8888
# token = "per-remote-token"   # 설정 시 공유 토큰보다 우선
```

### 2) JSON 파일

루트에 `jupyter_remote_exec.json` 파일을 둘 수도 있습니다.

```json
{
  "shared_token": "your_shared_token",
  "remotes": {
    "us-east": {"host": "east-server.example.com", "port": 8888, "https": true, "verify": false},
    "us-west": {"host": "west-server.example.com", "port": 8888}
  }
}
```

### 3) 환경 변수

- `JRE_SHARED_TOKEN`
- `JRE_DEFAULT_HTTPS` (true/false)
- `JRE_DEFAULT_VERIFY` (true/false/경로)
- 리모트별 오버라이드:
  - `JRE_REMOTE_<NAME>_HOST`
  - `JRE_REMOTE_<NAME>_PORT`
  - `JRE_REMOTE_<NAME>_HTTPS`
  - `JRE_REMOTE_<NAME>_VERIFY`
  - `JRE_REMOTE_<NAME>_TOKEN`

### 4) 런타임 코드로 설정

```python
from config import set_config

set_config({
  "shared_token": "your_shared_token",
  "remotes": {
    "us-east": {"host": "east", "port": 8888, "https": True, "verify": False},
    "us-west": {"host": "west", "port": 8888, "token": "per-remote-token"}
  }
})
```

### 토큰 우선순위
- 리모트별 토큰 (`remotes.<name>.token`)
- 공유 토큰 (`shared_token`)
- 미사용 (토큰 없이 접속; 서버가 허용해야 함)

레거시 방식(파일 내부에 상수 `REMOTE_CONFIG`, `SHARED_TOKEN`를 정의)은 더 이상 지원하지 않습니다. 반드시 `config.py` 또는 파일/환경변수/런타임 설정을 사용하세요.

HTTPS/WSS도 지원합니다. 각 리모트에서 `https=true`로 설정하면 REST는 `https://`, WebSocket은 `wss://`로 연결되며 `verify` 값에 따라 인증서 검증 동작을 제어합니다.

## 빠른 시작

### 1. 확장 로드

```ipython
%load_ext jupyter_remote_exec_magic_wrapper
```

### 2. 첫 번째 실행

```python
from jupyter_remote_exec import shell_on_remote

# 모든 리모트에서 코드 셀 실행
shell_on_remote("""
import sys
print('hello')
""")
```

출력 예시:
```
----- [ us-east ] ----------------------------------------
Hello from east-server.example.com!

----- [ us-west ] ----------------------------------------
Hello from west-server.example.com!
```

참고: 여러 리모트에서 실행하면 기본적으로 각 리모트별 구분선이 자동으로 추가되어 출력됩니다. 구분선은 `separators` 옵션으로 끌 수 있습니다(`separators=False`).

## 사용법

### 코드 셀 실행

여러 줄의 Python 코드 블록을 그대로 원격 커널에서 실행합니다. 셸의 `!` 슈가 문법은 지원하지 않습니다.

- `exec_cell_on_remote(block, remotes=None)` — 여러 줄 블록을 순서대로 실행

예시

```python
from jupyter_remote_exec import shell_on_remote

# 1) 간단한 코드 블록
shell_on_remote("""
import platform
print(platform.python_version())
""")

# 2) 특정 리모트에서만 실행
shell_on_remote("""
print('Hello from us-east')
""", 'us-east')

# 3) 여러 리모트에서 실행
shell_on_remote("""
import socket
print('Hi from', socket.gethostname())
""", ['us-east', 'us-west'])
```

### 기본 사용법

#### 모든 리모트에서 실행

```python
def my_task():
    import sys
    print(f"Python: {sys.executable}")

exec_on_remote(my_task)
```

#### 특정 리모트에서만 실행

```python
def check_disk():
    import os
    print(f"Current directory: {os.getcwd()}")

# 단일 리모트
exec_on_remote(check_disk, 'us-east')

# 여러 리모트
exec_on_remote(check_disk, ['us-east', 'us-west'])
```

#### 동적 리모트 선택

```python
# 사용 가능한 리모트 목록 가져오기
remotes = get_remotes()
print(f"Available remotes: {remotes}")

# 조건부 선택
use_asia = True
selected_remotes = ['asia-pacific'] if use_asia else ['us-east', 'us-west']

exec_on_remote(my_task, selected_remotes)
```


### 실전 예제

#### 예제 1: 환경 정보 수집

```python
def collect_info():
    import sys
    import os
    import socket
    import platform
    
    print(f"Hostname: {socket.gethostname()}")
    print(f"Platform: {platform.platform()}")
    print(f"Python: {sys.version}")
    print(f"Working directory: {os.getcwd()}")

exec_on_remote(collect_info)
```

#### 예제 2: 분산 데이터 처리

```python
def process_local_data():
    import pandas as pd
    
    # 각 리모트에서 로컬 데이터 처리
    df = pd.read_csv('/data/local_metrics.csv')
    result = df.groupby('category').sum()
    
    print("Summary:")
    print(result)

exec_on_remote(process_local_data, ['us-east', 'us-west'])
```

#### 예제 3: HDFS 사용량 조회

```python
def check_hdfs_usage():
    import subprocess
    
    # 1TB 이상 사용자 찾기
    result = subprocess.run(
        ['hdfs', 'dfs', '-du', '-h', '/user'],
        capture_output=True, text=True
    )
    
    lines = result.stdout.split('\n')
    large_users = [line for line in lines if 'T' in line]
    
    print("Users with >1TB:")
    for user in large_users:
        print(user)

# 모든 리전의 HDFS 체크
exec_on_remote(check_hdfs_usage)
```

## API 레퍼런스

### 함수

#### `exec_on_remote(func, remotes=None)`

지정된 리모트(들)에서 함수를 실행합니다.

**Parameters:**
- `func` (callable): 실행할 Python 함수
- `remotes` (str | list | None): 실행할 리모트 지정
    - `None`: 모든 리모트에서 실행
    - `'us-east'`: 단일 리모트에서 실행
    - `['us-east', 'us-west']`: 여러 리모트에서 실행

**Returns:** None (결과는 stdout으로 출력됨)

**Example:**
```python
def task():
    print("Hello!")

exec_on_remote(task)  # 모든 리모트
exec_on_remote(task, 'us-east')  # 단일 리모트
exec_on_remote(task, ['us-east', 'us-west'])  # 여러 리모트
```

#### `exec_cell_on_remote(code, remotes=None, *, separators=None)`

한 줄 또는 여러 줄의 Python 코드를 지정된 리모트(들)에서 실행합니다.

**Parameters:**
- `code` (str): 실행할 Python 코드 (단일 라인 또는 블록 모두 가능)
- `remotes` (str | list | None): 실행할 리모트 지정
    - `None`: 모든 리모트에서 실행
    - `'us-east'`: 단일 리모트에서 실행
    - `['us-east', 'us-west']`: 여러 리모트에서 실행
- `separators` (bool | None): 리모트별 구분선 출력 여부
    - `True`: 항상 구분선 출력
    - `False`: 구분선 미출력
    - `None`(기본): 여러 리모트 대상일 때만 자동으로 구분선 출력

**Returns:** None (결과는 stdout으로 출력됨)

**Example:**
```python
# 1) 단일 라인 코드
exec_cell_on_remote("print('hello')")

# 2) 멀티라인 블록
exec_cell_on_remote("""
import sys
print(sys.version)
""")

# 3) 특정 리모트에서 실행 + 구분선 비활성화
exec_cell_on_remote("print('Hello from us-east')", 'us-east', separators=False)
```

#### `get_remotes()`

사용 가능한 리모트 목록을 반환합니다.

**Returns:** `list[str]` - 리모트 이름 리스트

**Example:**
```python
remotes = get_remotes()
print(remotes)  # ['us-east', 'us-west', 'eu-central', 'asia-pacific']
```

### 매직 커맨드

현재 제공되는 매직은 확장 로드만입니다. 아래 명령으로 확장을 로드하면 `exec_on_remote`, `exec_cell_on_remote`, `get_remotes` 세 함수가 노트북 전역 네임스페이스에 바인딩됩니다.

```ipython
%load_ext jupyter_remote_exec_magic_wrapper
```

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

1. **커널 생성**: HTTP POST 요청으로 각 리모트에 Python 커널 생성
2. **코드 실행**: WebSocket을 통해 Jupyter 메시지 프로토콜로 코드 전송
3. **결과 수신**: IOPub 채널을 통해 stdout/stderr 수신 및 출력

## 제약사항

- 인증 토큰은 리모트별 또는 공유 토큰으로 설정할 수 있으며, 토큰 없이 접속하도록 서버가 허용할 수도 있습니다
- 함수는 `inspect.getsource()`로 추출 가능해야 합니다 (람다 함수는 제한적 지원)
- 네트워크 지연에 따라 실행 시간이 달라질 수 있습니다
- 함수 내부에서 사용하는 모듈은 각 리모트에 설치되어 있어야 합니다

## 기술 스택

- **Python**: 3.12+
- **Dependencies**:
    - `IPython` - 매직 커맨드 지원
    - `websocket-client` - WebSocket 통신
    - `requests` - HTTP 요청
    - `jupyter-server` - Jupyter 서버 연동

## 라이선스

MIT License