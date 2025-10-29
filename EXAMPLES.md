# jupyter-remote-exec 사용 예시

이 노트북은 jupyter-remote-exec 확장의 기본 사용법을 보여줍니다.

## 설정

먼저 확장을 로드합니다:

```python
%load_ext jupyter_remote_exec
```

## 예시 1: 기본 사용법

모든 리전에서 간단한 작업 실행:

```python
def hello():
    print("Hello from region!")
    import sys
    print(f"Python: {sys.executable}")

exec_on_region(hello)
```

## 예시 2: 특정 리전에서만 실행

```python
def check_hostname():
    import socket
    print(f"Hostname: {socket.gethostname()}")

# nj 리전에서만 실행
exec_on_region(check_hostname, 'nj')
```

## 예시 3: 여러 리전 선택

```python
def task():
    import time
    print(f"Current time: {time.time()}")

# nj와 wa 리전에서만 실행
exec_on_region(task, ['nj', 'wa'])
```

## 예시 4: 동적 리전 선택

```python
def process():
    import os
    print(f"Working directory: {os.getcwd()}")

# 리전 목록 가져오기
regions = get_regions()
print(f"Available regions: {regions}")

# 첫 번째 리전에서만 실행
exec_on_region(process, regions[0])
```

## 예시 5: 조건부 실행

```python
def compute():
    import random
    result = random.randint(1, 100)
    print(f"Random number: {result}")

# 조건에 따라 실행할 리전 선택
use_east_coast = True
regions_to_use = ['nj', 'va'] if use_east_coast else ['wa', 'ca']

exec_on_region(compute, regions_to_use)
```

## 예시 6: 리전 상태 확인

```python
%regions
```

## 예시 7: 데이터 처리

```python
def analyze_data():
    import pandas as pd
    import numpy as np
    
    # 샘플 데이터 생성
    data = pd.DataFrame({
        'value': np.random.randn(5)
    })
    
    print("Statistics:")
    print(data.describe())

exec_on_region(analyze_data)
```

## 예시 8: 환경 정보 수집

```python
def collect_env():
    import sys
    import platform
    
    print(f"Platform: {platform.platform()}")
    print(f"Python version: {sys.version}")
    print(f"Architecture: {platform.machine()}")

exec_on_region(collect_env)
```
