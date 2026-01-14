from gevent import monkey
monkey.patch_all()
from flask import Flask, request, send_from_directory, Response, jsonify, stream_with_context
from flask_socketio import SocketIO, emit
import requests
from QuarkPan.quark_client import create_client
import os
import atexit
import signal
import sys
import json
from typing import Dict, List, Tuple, Generator
import threading
import time
import re
import io
import traceback
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from math import ceil
import base64
app = Flask(__name__)
app.config['SECRET_KEY'] = 'you4sa4f65as1f5r-secreasft-ke154y-hhsfaere'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")
HOST_PASSWORD = "123"
global_state = {
    'host_sid': None,
    'host_nick': '',
    'time': 0,
    'paused': True,
    'url': '',
    'cookie': '',
    'quark_cookie': '',
    'quark_logged': False,
    'videoLoaded': False,
    'm3u8_base_url': '',
    'm3u8_content': None,
    'is_m3u8': False,
    'ts_urls': [],
    'ts_durations': []
}
connected_clients = {}
active_requests = {}
active_proxies = set()
class M3U8Processor:
    @staticmethod
    def extract_base_url(m3u8_url: str) -> str:
        parsed = urlparse(m3u8_url)
        path = parsed.path
        if '/' in path:
            path = path[:path.rfind('/') + 1]
        base_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            path,
            '',
            '',
            ''
        ))
        return base_url
    @staticmethod
    def download_m3u8(url: str, cookie: str = '') -> Tuple[str, List[str], str, List[float]]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
            'Referer': "https://pan.quark.cn/"
        }
        if cookie:
            headers['Cookie'] = cookie
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            m3u8_content = response.text
            base_url = M3U8Processor.extract_base_url(url)
            ts_urls = []
            durations = []
            lines = m3u8_content.split('\n')
            print(f"[M3U8] Total lines: {len(lines)}")
            print(f"[M3U8] Base URL: {base_url}")
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('#EXTINF:'):
                    try:
                        duration_str = line.split(':')[1].split(',')[0]
                        duration = float(duration_str)
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if (next_line.endswith('.ts') or '.ts?' in next_line) and not next_line.startswith('#'):
                                ts_urls.append(next_line)
                                durations.append(duration)
                                print(f"[M3U8] Found: duration={duration}, url={next_line[:50]}...")
                                i += 1
                    except (ValueError, IndexError) as e:
                        print(f"[M3U8] Error parsing duration line: {line}, error: {e}")
                i += 1
            print(f"[M3U8] Parsed {len(ts_urls)} TS segments, {len(durations)} durations")
            print(f"[M3U8] Sample TS URL: {ts_urls[0][:100] if ts_urls else 'None'}")
            if len(ts_urls) != len(durations):
                print(f"[M3U8] WARNING: TS count ({len(ts_urls)}) != duration count ({len(durations)})")
                min_len = min(len(ts_urls), len(durations))
                ts_urls = ts_urls[:min_len]
                durations = durations[:min_len]
            return m3u8_content, ts_urls, base_url, durations
        except Exception as e:
            print(f"[M3U8] Error downloading/parsing m3u8: {str(e)}")
            print(f"[M3U8] Traceback: {traceback.format_exc()}")
            raise
    @staticmethod
    def create_m3u8_playlist(base_url: str, ts_urls: List[str], durations: List[float], start_index: int = 0) -> str:
        import urllib.parse
        if len(ts_urls) != len(durations):
            print(f"[M3U8 Playlist] WARNING: Mismatch! {len(ts_urls)} TS URLs vs {len(durations)} durations")
            min_len = min(len(ts_urls), len(durations))
            ts_urls = ts_urls[:min_len]
            durations = durations[:min_len]
        playlist = "#EXTM3U\n"
        playlist += "#EXT-X-VERSION:3\n"
        target_duration = 5
        if durations:
            target_duration = max(int(ceil(max(durations))), 5)
        playlist += f"#EXT-X-TARGETDURATION:{target_duration}\n"
        playlist += "#EXT-X-MEDIA-SEQUENCE:0\n"
        playlist += "#EXT-X-PLAYLIST-TYPE:VOD\n"
        for i, (ts_url, duration) in enumerate(zip(ts_urls[start_index:], durations[start_index:])):
            encoded_base_url = urllib.parse.quote_plus(base_url)
            encoded_ts_url = urllib.parse.quote_plus(ts_url)
            proxy_url = f"/proxy_m3u8_ts?base_url={encoded_base_url}&ts_url={encoded_ts_url}&index={i}"
            playlist += f"#EXTINF:{duration:.3f},\n"
            playlist += f"{proxy_url}\n"
        playlist += "#EXT-X-ENDLIST\n"
        print(f"[M3U8 Playlist] Created playlist with {len(ts_urls[start_index:])} segments")
        return playlist
    @staticmethod
    def is_m3u8_url(url: str) -> bool:
        return '.m3u8' in url or url.endswith('/m3u8')
DEEPSEEK_API_KEY = "ms-ab182171-1e7e-453d-8d4f-ebd5aa9d15a5"
DEEPSEEK_API_URL = "https://api-inference.modelscope.cn/v1"
class DeepSeekAIClient:
    def __init__(self, user_id: str):
        self.api_key = DEEPSEEK_API_KEY
        self.base_url = DEEPSEEK_API_URL
        self.user_id = user_id
        self.max_history_length = 10
        self.max_tokens = 8000
        self.enable_thinking = True
    def checklen(self, text: List[Dict]) -> List[Dict]:
        while self.get_length(text) > 11000:
            del text[0]
        return text
    def get_length(self, text: List[Dict]) -> int:
        length = 0
        for content in text:
            temp = content["content"]
            length += len(temp)
        return length
    def get_answer_stream(self, message: List[Dict], enable_thinking: bool = True) -> Generator:
        try:
            try:
                from openai import OpenAI
                client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                )
                extra_body = {
                    "enable_thinking": enable_thinking,
                    "enable_search": True
                }
                response = client.chat.completions.create(
                    model='deepseek-ai/DeepSeek-V3.2',
                    messages=message,
                    stream=True,
                    extra_body=extra_body,
                    max_tokens=self.max_tokens
                )
                done_thinking = False
                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    thinking_chunk = getattr(delta, 'reasoning_content', '')
                    answer_chunk = getattr(delta, 'content', '')
                    if thinking_chunk:
                        yield {
                            'type': 'thinking',
                            'content': thinking_chunk,
                            'done_thinking': done_thinking
                        }
                    if answer_chunk:
                        if not done_thinking:
                            yield {
                                'type': 'thinking_end',
                                'content': '\n\n=== 最终回答 ===\n'
                            }
                            done_thinking = True
                        yield {
                            'type': 'answer',
                            'content': answer_chunk
                        }
            except ImportError:
                print(f"[AI] OpenAI package not available, using requests for user {self.user_id}")
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                payload = {
                    'model': 'deepseek-ai/DeepSeek-V3.2',
                    'messages': message,
                    'stream': True,
                    'max_tokens': self.max_tokens,
                    'extra_body': {
                        'enable_thinking': enable_thinking
                    }
                }
                response = requests.post(
                    f'{self.base_url}/chat/completions',
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=30
                )
                if response.status_code != 200:
                    raise Exception(f"API request failed with status {response.status_code}: {response.text}")
                done_thinking = False
                for line in response.iter_lines():
                    if not line:
                        continue
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if not chunk.get('choices'):
                                continue
                            delta = chunk['choices'][0].get('delta', {})
                            thinking_chunk = delta.get('reasoning_content', '')
                            answer_chunk = delta.get('content', '')
                            if thinking_chunk:
                                yield {
                                    'type': 'thinking',
                                    'content': thinking_chunk,
                                    'done_thinking': done_thinking
                                }
                            if answer_chunk:
                                if not done_thinking:
                                    yield {
                                        'type': 'thinking_end',
                                        'content': '\n\n=== 最终回答 ===\n'
                                    }
                                    done_thinking = True
                                yield {
                                    'type': 'answer',
                                    'content': answer_chunk
                                }
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"[AI] DeepSeek API请求错误 for user {self.user_id}: {e}")
            yield {
                'type': 'error',
                'content': f"AI服务暂时不可用: {str(e)}"
            }
    def chat(self, user_input: str, history: List[Dict] = None, enable_thinking: bool = True) -> Generator:
        if history is None:
            history = []
        history.append({"role": "user", "content": user_input})
        history = self.checklen(history)
        return self.get_answer_stream(history, enable_thinking)
def cleanup_all_connections():
    print(f"\n[Cleanup] Force closing {len(active_requests)} active streams...")
    for proxy_id, resp in list(active_requests.items()):
        try:
            resp.close()
            print(f"[Cleanup] Closed {proxy_id}")
        except:
            pass
    active_requests.clear()
    active_proxies.clear()
atexit.register(cleanup_all_connections)
signal.signal(signal.SIGINT, lambda sig, frame: (cleanup_all_connections(), sys.exit(0)))
signal.signal(signal.SIGTERM, lambda sig, frame: (cleanup_all_connections(), sys.exit(0)))
@app.route('/')
def home():
    return send_from_directory('.', 'index.html')
@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(path) and os.path.isfile(path):
        return send_from_directory('.', path)
    return "File not found", 404
@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    if not url:
        return "Missing 'url' parameter", 400
    cookie = request.args.get('cookie', '')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
        'Referer': 'https://pan.quark.cn/'
    }
    if request.headers.get('Range'):
        headers['Range'] = request.headers.get('Range')
    if cookie:
        headers['Cookie'] = cookie
    proxy_id = f"{url[:50]}_{id(request)}"
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        active_requests[proxy_id] = resp
        active_proxies.add(proxy_id)
        print(f"[Proxy] Started: {proxy_id} (active: {len(active_requests)})")
        def generate():
            try:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        if global_state['host_sid'] is None:
                            print(f"[Proxy] Host gone, stopping: {proxy_id}")
                            raise GeneratorExit()
                        yield chunk
            except GeneratorExit:
                raise
            except Exception as e:
                print(f"[Proxy] Error in stream {proxy_id}: {e}")
                raise
            finally:
                if resp:
                    resp.close()
                active_requests.pop(proxy_id, None)
                active_proxies.discard(proxy_id)
                print(f"[Proxy] Closed: {proxy_id}")
        response_headers = {
            'Content-Type': resp.headers.get('Content-Type', 'video/mp4'),
            'Accept-Ranges': 'bytes',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
        }
        for key in ('Content-Length', 'Content-Range', 'Accept-Ranges'):
            if key in resp.headers:
                response_headers[key] = resp.headers[key]
        return Response(generate(), status=resp.status_code, headers=response_headers, direct_passthrough=True)
    except Exception as e:
        active_requests.pop(proxy_id, None)
        active_proxies.discard(proxy_id)
        return f"Proxy failed: {e}", 500
@app.route('/proxy_m3u8_ts')
def proxy_m3u8_ts():
    import urllib.parse
    base_url = request.args.get('base_url')
    ts_url = request.args.get('ts_url')
    index = request.args.get('index', '0')
    if not base_url or not ts_url:
        return "Missing parameters", 400
    decoded_base_url = urllib.parse.unquote_plus(base_url)
    decoded_ts_url = urllib.parse.unquote_plus(ts_url)
    cookie = global_state.get('cookie', '')
    full_url = decoded_ts_url
    if not decoded_ts_url.startswith('http'):
        if not decoded_base_url.endswith('/'):
            decoded_base_url += '/'
        full_url = urllib.parse.urljoin(decoded_base_url, decoded_ts_url)
    print(f"[M3U8 Proxy] Downloading TS segment {index}")
    print(f"[M3U8 Proxy] Base URL: {decoded_base_url}")
    print(f"[M3U8 Proxy] TS URL: {decoded_ts_url[:100]}...")
    print(f"[M3U8 Proxy] Full URL: {full_url[:100]}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
        'Referer': "https://pan.quark.cn/",
        'Accept': '*/*',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive'
    }
    if cookie:
        headers['Cookie'] = cookie
    proxy_id = f"m3u8_ts_{index}_{id(request)}"
    try:
        resp = requests.get(full_url, headers=headers, stream=True, timeout=60)
        active_requests[proxy_id] = resp
        active_proxies.add(proxy_id)
        if resp.status_code != 200:
            print(f"[M3U8 Proxy] Failed to download TS segment {index}: {resp.status_code}")
            print(f"[M3U8 Proxy] Full URL: {full_url}")
            resp.close()
            return f"Failed to download TS segment: {resp.status_code}", 500
        def generate():
            try:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        if global_state['host_sid'] is None:
                            raise GeneratorExit()
                        yield chunk
            except GeneratorExit:
                raise
            except Exception as e:
                print(f"[M3U8 Proxy] Error in stream {proxy_id}: {e}")
                raise
            finally:
                if resp:
                    resp.close()
                active_requests.pop(proxy_id, None)
                active_proxies.discard(proxy_id)
        response_headers = {
            'Content-Type': 'video/MP2T',
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
            'Content-Length': resp.headers.get('Content-Length', ''),
        }
        return Response(generate(), status=200, headers=response_headers, direct_passthrough=True)
    except Exception as e:
        active_requests.pop(proxy_id, None)
        active_proxies.discard(proxy_id)
        print(f"[M3U8 Proxy] Exception for segment {index}: {str(e)}")
        print(f"[M3U8 Proxy] Failed URL: {full_url}")
        return f"Proxy failed: {e}", 500
@app.route('/m3u8_playlist')
def m3u8_playlist():
    if not global_state.get('is_m3u8', False) or not global_state.get('m3u8_content'):
        return "Not a m3u8 video or m3u8 content not loaded", 400
    base_url = global_state.get('m3u8_base_url', '')
    ts_urls = global_state.get('ts_urls', [])
    durations = global_state.get('ts_durations', [])
    if not base_url or not ts_urls:
        return "M3U8 data not available", 400
    playlist = M3U8Processor.create_m3u8_playlist(base_url, ts_urls, durations)
    return Response(playlist, mimetype='application/vnd.apple.mpegurl')
@socketio.on('connect')
def on_connect():
    print(f"[Socket] Connected: {request.sid}")
@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    nick = None
    if sid in connected_clients:
        nick = connected_clients[sid].get('nick', '未知')
        was_host = connected_clients[sid].get('is_host', False)
        del connected_clients[sid]
        emit('audience_list_update', get_audience_list(), broadcast=True)
        print(f"[Socket] Disconnected: {nick} ({sid})")
        role_text = "房主" if was_host else "观众"
        emit('system', f"{nick}({role_text}) 离开了房间", broadcast=True)
    if global_state['host_sid'] == sid:
        print(f"[Host] Host left ({global_state['host_nick']}), destroying room...")
        cleanup_all_connections()
        global_state.update({
            'host_sid': None, 'host_nick': '', 'url': '', 'cookie': '',
            'videoLoaded': False, 'time': 0, 'paused': True,
            'm3u8_base_url': '', 'm3u8_content': None, 'is_m3u8': False, 'ts_urls': [], 'ts_durations': []
        })
        global_state['quark_cookie'] = ''
        global_state['quark_logged'] = False
        emit('video_disconnected', "房主已离开，视频已中断", broadcast=True)
        emit('host_status_update', {'hostNick': '无人', 'isHost': False}, broadcast=True)
    if not connected_clients:
        print("[Cleanup] Room is empty, cleaning up all data...")
        cleanup_all_connections()
        global_state.update({
            'host_sid': None, 'host_nick': '', 'url': '', 'cookie': '',
            'videoLoaded': False, 'time': 0, 'paused': True,
            'quark_cookie': '', 'quark_logged': False,
            'm3u8_base_url': '', 'm3u8_content': None, 'is_m3u8': False, 'ts_urls': [], 'ts_durations': []
        })
        connected_clients.clear()
        print("[Cleanup] All room data has been reset")
@socketio.on('join')
def on_join(data):
    nick = data['nick']
    is_host = data.get('is_host', False)
    password = data.get('password', '')
    sid = request.sid
    connected_clients[sid] = {
        'sid': sid,
        'nick': nick,
        'is_host': False,
        'ai_history': [],
        'ai_enabled': True,
        'ai_client': None,
        'current_time': 0,
        'drift': 0,
        'last_sync_time': time.time()
    }
    if is_host:
        if global_state['host_sid'] is not None:
            is_host = False
            emit('role_forced_to_viewer', "已有房主，您被设为观众", room=sid)
        elif password != HOST_PASSWORD:
            emit('host_password_error', "房主密码错误", room=sid)
            return
        else:
            global_state['host_sid'] = sid
            global_state['host_nick'] = nick
            connected_clients[sid]['is_host'] = True
            emit('system', f"{nick} 成为房主，房间已激活", broadcast=True)
            emit('host_status_update', {'hostNick': nick, 'isHost': False}, broadcast=True)
    connected_clients[sid]['ai_client'] = DeepSeekAIClient(user_id=sid)
    emit('joined', {
        'isHost': connected_clients[sid]['is_host'],
        'hostNick': global_state['host_nick'] or '无人',
        'aiEnabled': connected_clients[sid]['ai_enabled']
    }, room=sid)
    if global_state['videoLoaded']:
        if global_state['is_m3u8']:
            proxy_url = f"/m3u8_playlist?t={int(time.time())}"
            emit('load_video', {
                'url': proxy_url,
                'cookie': global_state['cookie'],
                'is_m3u8': True
            }, room=sid)
        else:
            emit('load_video', {
                'url': global_state['url'],
                'cookie': global_state['cookie'],
                'is_m3u8': False
            }, room=sid)
        emit('playback_state', {
            'time': global_state['time'],
            'paused': global_state['paused']
        }, room=sid)
    role_text = "房主" if connected_clients[sid]['is_host'] else "观众"
    emit('system', f"{nick} 以{role_text}身份加入了房间", broadcast=True)
    emit('audience_list_update', get_audience_list(), broadcast=True)
@socketio.on('ai_chat')
def on_ai_chat(data):
    sid = request.sid
    user_input = data.get('message', '').strip()
    enable_thinking = data.get('enable_thinking', True)
    if not user_input:
        return
    user_data = connected_clients.get(sid)
    if not user_data:
        return
    if not user_data.get('ai_enabled', True):
        socketio.emit('ai_response', {
            'type': 'error',
            'nick': 'AI助手',
            'message': '您的AI助手已禁用，请先启用',
            'timestamp': time.time()
        }, room=sid)
        return
    nick = user_data['nick']
    def process_ai_response():
        try:
            ai_history = user_data.get('ai_history', [])
            ai_client = user_data.get('ai_client')
            if not ai_client:
                ai_client = DeepSeekAIClient(user_id=sid)
                user_data['ai_client'] = ai_client
            if len(ai_history) == 0:
                system_prompt = f"你是{nick}的私人AI助手。你们正在一个同步观看视频的房间中。你可以帮助用户了解各种常识问题。请以专业、风趣幽默的态度回答。"
                ai_history.append({"role": "system", "content": system_prompt})
            stream = ai_client.chat(user_input, ai_history, enable_thinking)
            full_response = ""
            thinking_content = ""
            done_thinking = False
            for chunk in stream:
                chunk_type = chunk.get('type')
                content = chunk.get('content', '')
                if chunk_type == 'thinking':
                    socketio.emit('ai_thinking', {
                        'nick': 'AI助手',
                        'message': content,
                        'is_thinking': True,
                        'timestamp': time.time()
                    }, room=sid)
                    thinking_content += content
                elif chunk_type == 'thinking_end':
                    done_thinking = True
                    socketio.emit('ai_thinking_end', {
                        'nick': 'AI助手',
                        'message': content,
                        'timestamp': time.time()
                    }, room=sid)
                elif chunk_type == 'answer':
                    full_response += content
                    socketio.emit('ai_response_stream', {
                        'nick': 'AI助手',
                        'message': content,
                        'done_thinking': done_thinking,
                        'timestamp': time.time()
                    }, room=sid)
                elif chunk_type == 'error':
                    socketio.emit('ai_response', {
                        'type': 'error',
                        'nick': 'AI助手',
                        'message': content,
                        'timestamp': time.time()
                    }, room=sid)
                    return
            if full_response:
                ai_history.append({"role": "assistant", "content": full_response})
                user_data['ai_history'] = ai_history
            socketio.emit('ai_response_complete', {
                'nick': 'AI助手',
                'message': full_response,
                'timestamp': time.time()
            }, room=sid)
        except Exception as e:
            print(f"[AI] Error processing AI request for user {sid}: {e}")
            print(f"[AI] Traceback: {traceback.format_exc()}")
            socketio.emit('ai_response', {
                'type': 'error',
                'nick': 'AI助手',
                'message': f'抱歉，处理您的请求时出现错误: {str(e)[:100]}',
                'timestamp': time.time()
            }, room=sid)
    thread = threading.Thread(target=process_ai_response)
    thread.daemon = True
    thread.start()
@socketio.on('clear_ai_history')
def on_clear_ai_history():
    sid = request.sid
    user_data = connected_clients.get(sid)
    if user_data:
        user_data['ai_history'] = []
        socketio.emit('ai_history_cleared', {}, room=sid)
        socketio.emit('system', f"{user_data['nick']} 清空了AI对话历史", room=sid)
@socketio.on('toggle_ai')
def on_toggle_ai(data):
    sid = request.sid
    user_data = connected_clients.get(sid)
    if user_data:
        enable = data.get('enable', None)
        if enable is None:
            user_data['ai_enabled'] = not user_data['ai_enabled']
        else:
            user_data['ai_enabled'] = bool(enable)
        status = "启用" if user_data['ai_enabled'] else "禁用"
        socketio.emit('ai_toggled', {
            'enabled': user_data['ai_enabled'],
            'message': f"AI助手已{status}"
        }, room=sid)
        socketio.emit('system', f"{user_data['nick']} {status}了AI助手", broadcast=True)
@socketio.on('load_video')
def on_load_video(data):
    if global_state['host_sid'] != request.sid:
        return
    url = data['url']
    cookie = data.get('cookie', '')
    video_name = data.get('videoName', '')
    is_m3u8 = M3U8Processor.is_m3u8_url(url)
    if is_m3u8:
        print(f"[M3U8] Loading m3u8 video: {url}")
        try:
            m3u8_content, ts_urls, base_url, durations = M3U8Processor.download_m3u8(url, cookie)
            global_state.update({
                'url': url,
                'cookie': cookie,
                'videoLoaded': True,
                'time': 0,
                'paused': True,
                'is_m3u8': True,
                'm3u8_content': m3u8_content,
                'm3u8_base_url': base_url,
                'ts_urls': ts_urls,
                'ts_durations': durations
            })
            proxy_url = f"/m3u8_playlist?t={int(time.time())}"
            emit('load_video', {
                'url': proxy_url,
                'cookie': cookie,
                'is_m3u8': True,
                'videoName': video_name
            }, broadcast=True)
            if video_name:
                emit('system', f"房主已更换视频：{video_name}（M3U8格式），正在加载...", broadcast=True)
            else:
                emit('system', "房主已更换视频（M3U8格式），正在加载...", broadcast=True)
            print(f"[M3U8] M3U8 video loaded successfully with {len(ts_urls)} segments")
        except Exception as e:
            emit('system', f"M3U8视频加载失败: {str(e)}", room=request.sid)
            print(f"[M3U8] Error loading m3u8 video: {str(e)}")
    else:
        global_state.update({
            'url': url,
            'cookie': cookie,
            'videoLoaded': True,
            'time': 0,
            'paused': True,
            'is_m3u8': False,
            'm3u8_content': None,
            'm3u8_base_url': '',
            'ts_urls': [],
            'ts_durations': []
        })
        emit('load_video', {
            'url': url,
            'cookie': cookie,
            'is_m3u8': False,
            'videoName': video_name
        }, broadcast=True)
        if video_name:
            emit('system', f"房主已更换视频：{video_name}，正在加载...", broadcast=True)
        else:
            emit('system', "房主已更换视频，正在加载...", broadcast=True)
@app.route('/quark/login', methods=['POST'])
def quark_login():
    data = request.json or {}
    sid = data.get('sid')
    cookie = data.get('cookie')
    if not sid or sid not in connected_clients:
        return jsonify({'error':'missing or invalid sid'}), 400
    if connected_clients[sid].get('is_host') is not True:
        return jsonify({'error':'only host can login to Quark'}), 403
    if not cookie:
        return jsonify({'error':'missing cookie'}), 400
    global_state['quark_cookie'] = ''
    global_state['quark_logged'] = False
    try:
        client = create_client(cookies=cookie, auto_login=False)
        result = client.list_files(folder_id='0')
        global_state['quark_cookie'] = cookie
        global_state['quark_logged'] = True
        return jsonify({'status':'ok','data':result})
    except Exception as e:
        global_state['quark_cookie'] = ''
        global_state['quark_logged'] = False
        return jsonify({'error':str(e)}), 400
@app.route('/quark/files')
def quark_files():
    sid = request.args.get('sid')
    folder_id = request.args.get('folder_id', '0')
    if not sid or sid not in connected_clients:
        return jsonify({'error':'missing or invalid sid'}), 400
    if connected_clients[sid].get('is_host') is not True:
        return jsonify({'error':'only host can browse files'}), 403
    if not global_state.get('quark_logged') or not global_state.get('quark_cookie'):
        return jsonify({'error':'not logged in to quark'}), 403
    cookie = global_state['quark_cookie']
    try:
        client = create_client(cookies=cookie, auto_login=False)
        result = client.list_files(folder_id=folder_id)
        return jsonify({'status':'ok','data':result.get('data', result)})
    except Exception as e:
        return jsonify({'error':str(e)}), 500
@app.route('/quark/play')
def quark_play():
    sid = request.args.get('sid')
    fid = request.args.get('fid')
    if not sid or sid not in connected_clients:
        return jsonify({'error':'missing or invalid sid'}), 400
    if connected_clients[sid].get('is_host') is not True:
        return jsonify({'error':'only host can request play url'}), 403
    if not fid:
        return jsonify({'error':'missing fid'}), 400
    cookie = global_state.get('quark_cookie')
    if not cookie:
        return jsonify({'error':'not logged in to quark'}), 403
    api_url = 'https://drive-pc.quark.cn/1/clouddrive/file/v2/play?pr=ucpro&fr=pc&uc_param_str='
    payload = {
        "fid": fid,
        "resolutions": "normal,low,high,super,2k,4k",
        "supports": "fmp4,m3u8"
    }
    def parse_cookie_string_to_dict(s):
        cookies = {}
        for pair in s.split(';'):
            pair = pair.strip()
            if not pair or '=' not in pair:
                continue
            k, v = pair.split('=', 1)
            cookies[k.strip()] = v.strip()
        return cookies
    cookies = parse_cookie_string_to_dict(cookie)
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json;charset=UTF-8',
        'Origin': 'https://pan.quark.cn',
        'Referer': 'https://pan.quark.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
    }
    try:
        r = requests.post(api_url, json=payload, headers=headers, cookies=cookies, timeout=15)
        if r.status_code != 200:
            return jsonify({'error':f'API请求失败: {r.status_code}, {r.text}'}), 500
        data = r.json()
        video_urls = {}
        m3u8_urls = {}
        mp4_urls = {}
        prefer_order = ['4k','2k','super','high','normal','low']
        video_list = data.get('data',{}).get('video_list',[])
        for v in video_list:
            vi = v.get('video_info',{})
            res = vi.get('resolution')
            url = vi.get('url')
            if res and url:
                if '.m3u8' in url:
                    m3u8_urls[res] = url
                else:
                    mp4_urls[res] = url
                video_urls[res] = url
        main_url = ''
        for res in prefer_order:
            if video_urls.get(res):
                main_url = video_urls[res]
                break
        if not main_url and video_urls:
            main_url = list(video_urls.values())[0]
        if not main_url:
            return jsonify({'error': '视频链接获取失败', 'raw':data}), 400
        return jsonify({
            'url': main_url,
            'allUrls': video_urls,
            'm3u8Urls': m3u8_urls,
            'mp4Urls': mp4_urls,
            'hasM3U8': len(m3u8_urls) > 0,
            'hasMP4': len(mp4_urls) > 0
        })
    except Exception as e:
        return jsonify({'error':str(e)}), 500
@app.route('/quark/logout', methods=['POST'])
def quark_logout():
    data = request.json or {}
    sid = data.get('sid')
    if not sid or sid not in connected_clients:
        return jsonify({'error':'missing or invalid sid'}), 400
    if connected_clients[sid].get('is_host') is not True:
        return jsonify({'error':'only host can logout quark'}), 403
    global_state['quark_cookie'] = ''
    global_state['quark_logged'] = False
    return jsonify({'status':'ok'})
@app.route('/quark/file_info')
def quark_file_info():
    sid = request.args.get('sid')
    fid = request.args.get('fid')
    if not sid or sid not in connected_clients:
        return jsonify({'error':'missing or invalid sid'}), 400
    if connected_clients[sid].get('is_host') is not True:
        return jsonify({'error':'only host can query file info'}), 403
    if not fid:
        return jsonify({'error':'missing fid'}), 400
    cookie = global_state.get('quark_cookie')
    if not cookie:
        return jsonify({'error':'not logged in to quark'}), 403
    try:
        client = create_client(cookies=cookie, auto_login=False)
        info = client.get_file_info(fid)
        return jsonify({'status':'ok','data':info})
    except Exception as e:
        return jsonify({'error':str(e)}), 500
@app.route('/quark/status')
def quark_status():
    sid = request.args.get('sid')
    if not sid or sid not in connected_clients:
        return jsonify({'error':'missing or invalid sid'}), 400
    if connected_clients[sid].get('is_host') is not True:
        return jsonify({'error':'only host can check quark status'}), 403
    cookie = global_state.get('quark_cookie') or ''
    cookie_mask = ''
    if cookie:
        cookie_mask = f"{cookie[:6]}...{cookie[-6:]}" if len(cookie) > 12 else '***'
    return jsonify({'logged': bool(global_state.get('quark_logged', False)), 'cookie_mask': cookie_mask})
@socketio.on('control')
def on_control(data):
    if global_state['host_sid'] != request.sid:
        return
    action = data.get('action')
    time = data.get('time')
    if time is not None:
        global_state['time'] = time
    if action == 'play':
        global_state['paused'] = False
    elif action == 'pause':
        global_state['paused'] = True
    emit('playback_state', {
        'time': global_state['time'],
        'paused': global_state['paused']
    }, broadcast=True, include_self=False)
@socketio.on('sync_request')
def on_sync_request(data=None):
    if global_state['videoLoaded'] and global_state['host_sid']:
        emit('playback_state', {
            'time': global_state['time'],
            'paused': global_state['paused']
        }, room=request.sid)
@socketio.on('chat')
def on_chat(data):
    emit('chat', {'nick': data['nick'], 'msg': data['msg']}, broadcast=True)
@socketio.on('viewer_sync_state')
def on_viewer_sync_state(data):
    sid = request.sid
    if sid not in connected_clients:
        return
    if connected_clients[sid].get('is_host'):
        return
    current_time = data.get('current_time', 0)
    drift = data.get('drift', 0)
    connected_clients[sid]['current_time'] = current_time
    connected_clients[sid]['drift'] = drift
    connected_clients[sid]['last_sync_time'] = time.time()
@socketio.on('get_audience_list')
def on_get_audience_list():
    if global_state['host_sid'] == request.sid:
        emit('audience_list', get_audience_list(), room=request.sid)
@socketio.on('kick_audience')
def on_kick_audience(data):
    if global_state['host_sid'] != request.sid:
        return
    target_sid = data['sid']
    if target_sid in connected_clients and target_sid != request.sid:
        nick = connected_clients[target_sid]['nick']
        emit('kicked', "你已被房主踢出", room=target_sid)
        socketio.server.disconnect(target_sid)
        emit('system', f"{nick} 被房主踢出", broadcast=True)
def get_audience_list():
    return [
        {
            'sid': sid,
            'nick': c['nick'],
            'current_time': c.get('current_time', 0),
            'drift': c.get('drift', 0),
            'last_sync_time': c.get('last_sync_time', 0)
        }
        for sid, c in connected_clients.items() if not c.get('is_host')
    ]
if __name__ == '__main__':
    print("一起看电视服务器启动成功！")
    print("访问地址: http://127.0.0.1:5000")
    print(f"房主密码: {HOST_PASSWORD}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)