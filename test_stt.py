import urllib.request, json
with open('bridge/captures/segment-1779365989870013600.wav', 'rb') as f:
    wav_bytes = f.read()

boundary = '----marimo-boundary123'
parts = [
    f'--{boundary}\r\n'.encode('utf-8'),
    b'Content-Disposition: form-data; name="audio"; filename="test.wav"\r\nContent-Type: audio/wav\r\n\r\n',
    wav_bytes,
    b'\r\n',
    f'--{boundary}--\r\n'.encode('utf-8')
]
body = b''.join(parts)
req = urllib.request.Request('http://127.0.0.1:8002/stt?model=fast', data=body, method='POST')
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
try:
    with urllib.request.urlopen(req) as res:
        print(res.read().decode())
except Exception as e:
    print(e)
