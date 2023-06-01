# Vidtheta

Website: https://vidtheta.streamlit.app/

Project Info: https://devpost.com/software/vidtheta

The documentation website: https://docs.thetatoken.org/docs/theta-video-api-developer-api was very helpful in implementing the project.

Other useful websites to refer:
- https://www.thetatoken.org/
- https://www.thetavideoapi.com/
- https://www.youtube.com/@thetalabs6835
- https://medium.com/theta-network/meet-the-winners-of-the-theta-hackathon-q1-2022-b8feddf429b9
- https://medium.com/theta-network/new-theta-video-api-service-gives-developers-power-to-bring-web-3-0-20bada2b1fab
- https://medium.com/@thetalabs

# Useful THETA video functions
```python
# -- Fetch URL
def create_presigned_url(id_key, secret_key):
    url = "https://api.thetavideoapi.com/upload"

    headers = {
        'x-tva-sa-id': id_key,
        'x-tva-sa-secret': secret_key,
    }

    response = requests.request("POST", url, headers=headers)

    return response.json()
```    

```python
# -- Upload video to presigned URL
def upload_video(presigned_url):
    headers = {
        'Content-Type': 'application/octet-stream'
    }

    with open("temp_video.mp4","rb") as f:
        data = f.read()

    response = requests.put(presigned_url, headers=headers, data = data)

    return response
```    

```python
# -- Transcode video
def transcode_video(id_key, secret_key, upload_id):
    url = "https://api.thetavideoapi.com/video"

    headers = {
    'x-tva-sa-id': id_key,
    'x-tva-sa-secret': secret_key,
    'Content-Type': 'application/json',
    }

    data = {
        "source_upload_id": upload_id,
        "playback_policy": "public",
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))

    return response.json()["body"]["videos"][0]["id"]
```    
