# jupyter-remote-exec

분산 컴퓨팅 환경을 위한 IPython 매직 확장입니다. 여러 원격 Jupyter 서버에서 동일한 코드를 실행하거나 특정 리모트에서만 코드를 선택적으로 실행할 수 있습니다.

## 주요 기능

- ✅ 여러 리모트에서 동시에 코드 실행
- ✅ 특정 리모트 선택 실행
- ✅ 함수형 프로그래밍 스타일 지원
- ✅ 자동 커널 관리
- ✅ WebSocket 기반 원격 실행

## 설치

### 방법 1: IPython 확장 디렉토리에 복사 (권장)

```bash
mkdir -p ~/.ipython/extensions
cp jupyter-remote-exec.py ~/.ipython/extensions/jupyter_remote_exec.py
```

### 방법 2: 현재 디렉토리에서 사용

```python
# Jupyter Notebook에서
%load_ext jupyter_remote_exec
```

## 설정

`jupyter-remote-exec.py` (또는 복사한 `~/.ipython/extensions/jupyter_remote_exec.py`) 파일을 열어 리모트 정보를 설정하세요:

```python
REMOTE_CONFIG = {
    'us-east': {'host': 'east-server.example.com', 'port': 8888},
    'us-west': {'host': 'west-server.example.com', 'port': 8888},
    'eu-central': {'host': 'eu-server.example.com', 'port': 8888},
    'asia-pacific': {'host': 'asia-server.example.com', 'port': 8888},
}

SHARED_TOKEN = 'your_jupyter_token_here'
```

## 빠른 시작

### 1. 확장 로드

```python
%load_ext jupyter_remote_exec
```

### 2. 첫 번째 실행

```python
def hello():
    import socket
    print(f"Hello from {socket.gethostname()}!")

# 모든 리모트에서 실행
exec_on_remote(hello)
```

출력 예시:
```
==================================================
Remote: us-east
==================================================
Hello from east-server.example.com!

==================================================
Remote: us-west
==================================================
Hello from west-server.example.com!

...
```

## 사용법

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

### 매직 커맨드

#### 리모트 상태 확인

```python
%remotes
```

출력 예시:
```
Available remotes:
  🟢 ACTIVE us-east: east-server.example.com:8888 (kernel: c900984c...)
  🔵 ready us-west: west-server.example.com:8888 (kernel: d19f0a2b...)
  ⚪ not initialized eu-central: eu-server.example.com:8888
  ⚪ not initialized asia-pacific: asia-server.example.com:8888

🟢 ACTIVE: LOCAL
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

#### `get_remotes()`

사용 가능한 리모트 목록을 반환합니다.

**Returns:** `list[str]` - 리모트 이름 리스트

**Example:**
```python
remotes = get_remotes()
print(remotes)  # ['us-east', 'us-west', 'eu-central', 'asia-pacific']
```

### 매직 커맨드

#### `%remotes`

모든 리모트의 상태를 출력합니다. 각 리모트의 연결 상태, 호스트 정보, 커널 ID를 보여줍니다.

**Usage:**
```python
%remotes
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

- 각 리모트의 Jupyter 서버는 동일한 인증 토큰을 사용해야 합니다
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