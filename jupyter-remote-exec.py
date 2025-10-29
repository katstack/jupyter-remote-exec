"""
Jupyter Remote Exec (jupyter-remote-exec) IPython Extension

IPython 매직 확장으로 여러 원격 Jupyter 서버(리전)에서 코드를 실행할 수 있습니다.
분산 컴퓨팅 환경에서 동일한 코드를 여러 리전에서 동시에 실행하거나 
특정 리전에서만 실행할 수 있는 기능을 제공합니다.

Author: whya5448
Date: 2025-10-29
"""

from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython import get_ipython
import websocket
import requests
import json
import uuid

# ============================================================================
# 설정
# ============================================================================

# 리전 설정: 각 리전의 호스트와 포트 정보
REGION_CONFIG = {
    'us-east': {'host': 'localhost', 'port': 8889},
    'us-west': {'host': 'localhost', 'port': 8890},
    'eu-central': {'host': 'localhost', 'port': 8891},
    'asia-pacific': {'host': 'localhost', 'port': 8892},
    # 필요에 따라 추가 리전 설정
}

# 모든 리전에서 공통으로 사용하는 인증 토큰
SHARED_TOKEN = 'your_token_here'

# ============================================================================
# 매직 클래스
# ============================================================================

@magics_class
class RegionMagics(Magics):
    """
    분산 리전에서 코드를 실행하기 위한 IPython 매직 클래스
    
    주요 기능:
    - exec_on_region(): 함수를 특정 리전에서 실행
    - get_regions(): 사용 가능한 리전 목록 조회
    - %region: 현재 실행 컨텍스트를 특정 리전으로 전환
    - %regions: 모든 리전의 상태 조회
    """
    
    def __init__(self, shell):
        """
        매직 확장 초기화
        
        Args:
            shell: IPython InteractiveShell 인스턴스
        """
        super().__init__(shell)
        self.current_region = None  # 현재 활성화된 리전 (None = local)
        self.active_kernels = {}    # 활성화된 커널 정보 저장
        
        # 전역 네임스페이스에 함수 등록
        shell.user_ns['exec_on_region'] = lambda f, r=None: self.exec_on_region(f, r)
        shell.user_ns['get_regions'] = lambda: self.get_regions()
        
        print(f"✅ jupyter-remote-exec loaded. Available regions: {list(REGION_CONFIG.keys())}")

    # ------------------------------------------------------------------------
    # 공개 API 함수
    # ------------------------------------------------------------------------

    def get_regions(self):
        """
        사용 가능한 리전 목록 반환
        
        Returns:
            list: 리전 이름 목록
            
        Example:
            >>> regions = get_regions()
            >>> print(regions)
            ['us-east', 'us-west', 'eu-central', 'asia-pacific']
        """
        return list(REGION_CONFIG.keys())

    def exec_on_region(self, func, regions=None):
        """
        지정된 리전(들)에서 함수 실행
        
        Args:
            func: 실행할 Python 함수
            regions: 실행할 리전 지정
                - None: 모든 리전에서 실행
                - str: 단일 리전에서 실행 (예: 'us-east')
                - list: 여러 리전에서 실행 (예: ['us-east', 'us-west'])
                
        Example:
            >>> def my_task():
            ...     import sys
            ...     print(sys.executable)
            
            >>> # 모든 리전에서 실행
            >>> exec_on_region(my_task)
            
            >>> # 특정 리전에서만 실행
            >>> exec_on_region(my_task, 'us-east')
            
            >>> # 여러 리전에서 실행
            >>> exec_on_region(my_task, ['us-east', 'us-west'])
        """
        # regions 인자를 리스트로 정규화
        if regions is None:
            region_list = list(REGION_CONFIG.keys())
        elif isinstance(regions, str):
            region_list = [regions]
        else:
            region_list = regions
        
        # 함수의 소스 코드 추출
        import inspect
        source = inspect.getsource(func)
        code = source + f"\n{func.__name__}()"
        
        # 각 리전에서 순차적으로 실행
        for region_name in region_list:
            # 로컬 실행 처리
            if region_name == 'local':
                print(f"\n{'='*50}")
                print(f"Region: LOCAL")
                print(f"{'='*50}")
                func()
                continue
            
            # 유효하지 않은 리전 체크
            if region_name not in REGION_CONFIG:
                print(f"❌ Unknown region: {region_name}")
                continue
            
            # 커널 준비 (없으면 생성)
            if not self._ensure_kernel(region_name):
                continue
            
            # 리전 헤더 출력
            print(f"\n{'='*50}")
            print(f"Region: {region_name}")
            print(f"{'='*50}")
            
            # 원격 실행
            region_info = self.active_kernels[region_name]
            output = self.execute_remote(region_info, code)
            print(output, end='')

    # ------------------------------------------------------------------------
    # 매직 커맨드
    # ------------------------------------------------------------------------

    @line_magic
    def region(self, line):
        """
        현재 실행 컨텍스트를 특정 리전으로 전환
        
        Usage:
            %region us-east    # us-east 리전으로 전환
            %region local      # 로컬 실행으로 복귀
            
        Note:
            이 명령어 이후 실행되는 모든 코드는 지정된 리전에서 실행됩니다.
        """
        region_name = line.strip()

        if region_name == 'local':
            self.current_region = None
            print(f"✅ Switched to LOCAL execution")
            return

        if region_name not in REGION_CONFIG:
            print(f"❌ Unknown region: {region_name}")
            print(f"Available regions: {list(REGION_CONFIG.keys())}")
            return

        # 커널이 없으면 생성
        if not self._ensure_kernel(region_name):
            return

        self.current_region = region_name
        print(f"✅ Switched to region: {region_name}")

    @line_magic
    def regions(self, line):
        """
        모든 리전의 상태 출력
        
        Usage:
            %regions
            
        각 리전의 연결 상태와 커널 정보를 표시합니다.
        """
        print("Available regions:")
        for name in REGION_CONFIG.keys():
            if name in self.active_kernels:
                status = "🟢 ACTIVE" if name == self.current_region else "🔵 ready"
                info = self.active_kernels[name]
                print(f"  {status} {name}: {info['host']}:{info['port']} (kernel: {info['kernel_id'][:8]}...)")
            else:
                status = "⚪ not initialized"
                config = REGION_CONFIG[name]
                print(f"  {status} {name}: {config['host']}:{config['port']}")

        if self.current_region is None:
            print(f"\n🟢 ACTIVE: LOCAL")

    # ------------------------------------------------------------------------
    # 내부 헬퍼 함수
    # ------------------------------------------------------------------------

    def _ensure_kernel(self, region_name):
        """
        리전에 커널이 존재하는지 확인하고, 없으면 생성
        
        Args:
            region_name: 리전 이름
            
        Returns:
            bool: 커널 준비 성공 여부
        """
        # 이미 커널이 있으면 성공
        if region_name in self.active_kernels:
            return True

        if region_name not in REGION_CONFIG:
            return False

        # 리전 설정 가져오기
        config = REGION_CONFIG[region_name]
        host = config['host']
        port = config['port']

        print(f"🔧 Creating kernel for region '{region_name}'...")

        # Jupyter Server API로 커널 생성 요청
        headers = {'Authorization': f'Token {SHARED_TOKEN}'}
        try:
            response = requests.post(
                f'http://{host}:{port}/api/kernels',
                headers=headers
            )

            if response.status_code == 201:
                kernel_info = response.json()
                kernel_id = kernel_info['id']
                
                # 커널 정보 저장
                self.active_kernels[region_name] = {
                    'host': host,
                    'port': port,
                    'kernel_id': kernel_id
                }
                print(f"✅ Kernel created: {kernel_id[:8]}...")
                return True
            else:
                print(f"❌ Failed to create kernel: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating kernel: {e}")
            return False

    def execute_remote(self, region_info, code):
        """
        원격 커널에서 코드 실행
        
        Jupyter의 WebSocket 프로토콜을 사용하여 원격 커널과 통신합니다.
        
        Args:
            region_info: 리전 정보 딕셔너리 (host, port, kernel_id)
            code: 실행할 Python 코드 문자열
            
        Returns:
            str: 실행 결과 출력 (stdout)
        """
        host = region_info['host']
        port = region_info['port']
        kernel_id = region_info['kernel_id']

        # WebSocket 연결
        ws_url = f'ws://{host}:{port}/api/kernels/{kernel_id}/channels?token={SHARED_TOKEN}'
        ws = websocket.create_connection(ws_url)

        # 고유 세션 및 메시지 ID 생성
        session_id = str(uuid.uuid4())
        msg_id = str(uuid.uuid4())

        # Jupyter 메시지 프로토콜에 따른 execute_request 메시지 생성
        msg = {
            'channel': 'shell',
            'header': {
                'msg_id': msg_id,
                'msg_type': 'execute_request',
                'session': session_id,
                'username': 'test',
                'version': '5.3',
                'date': ''
            },
            'parent_header': {},
            'metadata': {},
            'content': {
                'code': code,
                'silent': False,
                'store_history': True,
                'user_expressions': {},
                'allow_stdin': False
            }
        }

        # 메시지 전송
        ws.send(json.dumps(msg))

        # 결과 수신
        outputs = []
        while True:
            result = json.loads(ws.recv())
            parent_msg_id = result.get('parent_header', {}).get('msg_id', '')

            # 우리가 보낸 메시지에 대한 응답만 처리
            if parent_msg_id != msg_id:
                continue

            msg_type = result['msg_type']

            # stdout 출력 수집
            if msg_type == 'stream':
                outputs.append(result['content']['text'])

            # 실행 완료 확인
            if msg_type == 'status' and result['content']['execution_state'] == 'idle':
                break

        ws.close()
        return ''.join(outputs)

# ============================================================================
# 확장 로드/언로드
# ============================================================================

def load_ipython_extension(ipython):
    """
    IPython 확장 로드 함수
    
    %load_ext jupyter_remote_exec 실행 시 자동으로 호출됩니다.
    """
    ipython.register_magics(RegionMagics)

def unload_ipython_extension(ipython):
    """
    IPython 확장 언로드 함수
    
    %unload_ext jupyter_remote_exec 실행 시 자동으로 호출됩니다.
    """
    # 전역 네임스페이스에서 함수 제거
    if 'exec_on_region' in ipython.user_ns:
        del ipython.user_ns['exec_on_region']
    if 'get_regions' in ipython.user_ns:
        del ipython.user_ns['get_regions']