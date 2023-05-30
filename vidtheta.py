# Import necessary libraries
import streamlit as st # 1.10
from deepgram import Deepgram
import json
from moviepy.editor import VideoFileClip
import requests
from sentence_transformers import SentenceTransformer, util
import pickle
import os
import datetime
from time import sleep

# THETA functions
# -- Fetch URL
def create_presigned_url(id_key, secret_key):
    url = "https://api.thetavideoapi.com/upload"

    headers = {
        'x-tva-sa-id': id_key,
        'x-tva-sa-secret': secret_key,
    }

    response = requests.request("POST", url, headers=headers)

    return response.json()


# -- Upload video to presigned URL
def upload_video(presigned_url):
    headers = {
        'Content-Type': 'application/octet-stream'
    }

    with open("temp_video.mp4","rb") as f:
        data = f.read()

    response = requests.put(presigned_url, headers=headers, data = data)

    return response


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


# Page configurations
st.set_page_config(page_title="VidTheta",page_icon="🎥")
deepgram_api_key= "b1222616e4aba06853750bb268672cf95c5e36fa"
deepgram = Deepgram(deepgram_api_key)
chat_key = st.secrets["chat_key"]

# WebPage
st.title("Vidtheta🎥")
st.write("---")


st.sidebar.title("VidTheta🎥")
page = st.sidebar.radio("Select Page:", ('Upload','Search'))

# Load Sentence Similarity Model
# Vectorizes summaries of news articles and embeds them for later retrieval
#@st.cache
def load_model():
    return SentenceTransformer('msmarco-distilbert-base-tas-b')


# Handle local storage files -- can be replaced in the future with Theta EdgeStore    

# functionize this --!!! and cache it
# -- summaries of uploaded videos
if os.path.exists('summaries_array.pickle'):
    with open('summaries_array.pickle','rb') as file:
        video_summaries_array = pickle.load(file)

else:
    video_summaries_array = []

# -- metadata of uploaded videos
if os.path.exists('metadatas_array.pickle'):
    with open('metadatas_array.pickle','rb') as file:
        video_metadatas_array = pickle.load(file)

else:
    video_metadatas_array = []   


if page == "Upload":

    #st.components.v1.iframe("https://player.thetavideoapi.com/video/video_vtvuzy918z62ebypmi4165dztg")

    st.header("Upload Video📤")
    # Video uploader
    with st.form("video_details"):
        video_file = st.file_uploader("Please upload your MP4 video file:",["mp4"])
        video_title = st.text_input("Video Title","")
        st.text("Replace below details with your own")
        user_api_key = st.text_input("Your API key / x-tva-sa-id","srvacc_jeipuwjkg6ar5ac2ccfqrfe5u",type="password")
        user_api_secret = st.text_input("Your API secret / x-tva-sa-secret","sct8xxc8jc9ee6kmp2gkc5qfywx29qu4",type="password")
        submitted = st.form_submit_button("Upload 📤")

        if submitted:

            if video_file is not None and video_title != "":

                with open("temp_video.mp4", "wb") as f:
                    f.write(video_file.getvalue())
                    
                    sleep(0.2)

                # audio extract
                def extract_audio(input_video, output_audio):
                    video = VideoFileClip(input_video)
                    audio = video.audio
                    audio.write_audiofile(output_audio)

                input_video = 'temp_video.mp4'
                output_audio = 'temp_audio.mp3'

                extract_audio(input_video, output_audio)  
                sleep(0.2)


                # Audio Intelligence Function
                #@st.cache
                def audio_process(file):
                    with open("temp_audio.mp3",'rb') as audio:
                        source = {'buffer': audio, 'mimetype': 'audio/mp3'} 
                        response = deepgram.transcription.sync_prerecorded(source, {'paragraphs': True})
                    return response # dictionary


                with st.spinner("Loading..."):
                    result = audio_process(output_audio) 
                    #st.write(result)

                    req_res = result["results"]["channels"][0]["alternatives"][0]
                    transcript = req_res["transcript"]
                    st.header("Full Transcript")
                    st.write(transcript)
                    

                    paragraphs = req_res["paragraphs"]["paragraphs"]
                    final_para = []
                    for x in paragraphs:
                        for y in x["sentences"]:
                            final_para.append(f"{round(y['start'],2)}: {y['text']}")

                    final_para = "\n\n".join(final_para)        
                    st.header("Paragraphs with Starts")
                    st.write(final_para) 


                # Summarization and Chapters
                #@st.cache
                def sumchap(content):
                    URL = "https://api.openai.com/v1/chat/completions"
                    
                    payload = {
                        "model" : "gpt-3.5-turbo",
                        "temperature" : 0.7,
                        "max_tokens" : 1000,
                        "messages" : [
                            {"role":"system", "content": "You are a helpful assistant"},
                            {"role":"user"  , "content": f"First summarize the below captions of a video and then generate only important chapters with correct timestamp. \n {content}"}
                        ]
                    }

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {chat_key}"
                    }

                    llm_result = requests.post(URL, headers = headers, json = payload).json()
                    generated_content = llm_result['choices'][0]['message']['content']
                    return generated_content


                with st.spinner("Generating Metadata"):
                    sumchap_result = sumchap(final_para)
                    st.header("Summarization and Chapters")
                    st.write(sumchap_result)

                with st.spinner("Uploading Video..."):
                    url_res = create_presigned_url(user_api_key, user_api_secret)
                    presigned_url = url_res["body"]["uploads"][0]["presigned_url"]
                    upload_id = url_res["body"]["uploads"][0]["id"]
                    upload_res = upload_video(presigned_url)

                with st.spinner("Transcoding Video..."):
                    video_embed_id = transcode_video(user_api_key, user_api_secret, upload_id)
   
                
                with st.spinner("Updating Video database index..."):
                    # Calculate vector embedding
                    embedder = load_model()

                    summary_embedding = embedder.encode(sumchap_result.split("\n")[0])
                    video_summaries_array.append(summary_embedding)
                    video_metadatas_array.append((video_title, video_embed_id, datetime.datetime.now().date(),datetime.datetime.now().time(), transcript, final_para, sumchap_result)) # title, id, date of upload, time of upload, full transcript, Paragraph with starts, summary and chapters    

                    with open("summaries_array.pickle","wb") as file:
                        pickle.dump(video_summaries_array, file)

                    with open("metadatas_array.pickle","wb") as file:
                        pickle.dump(video_metadatas_array, file)

                    st.success("Video Indexed Successfully")
                    st.success("Video Uploaded Successfully") 
                    st.write("Video can be accessed at:")   
                    st.markdown(f"Theta Video Link: [Link](https://player.thetavideoapi.com/video/{video_metadatas_array[-1][1]})")
                    st.caption("It may take a few seconds for the encoding of the video to complete. Try the link after a few seconds")

                # unlatent demo link -- final video render on the website
                #st.components.v1.iframe("https://player.thetavideoapi.com/video/video_vtvuzy918z62ebypmi4165dztg")
            
            else:
                st.warning("Please upload a video file and title")



# Search Videos Page
elif page == "Search":
    #st.write(video_metadatas_array)


    if len(video_summaries_array) == 0:
        st.info("No videos found. Please upload first")

    st.header("Search Videos🔍")    

    search_query = st.text_input("Enter Search Query","")
    
    if st.button("Search"):
        with st.spinner("Searching Video Index..."):
            if search_query != "":
                embedder = load_model()    

                search_query_embedding = embedder.encode(search_query)
                cos_sim = util.cos_sim(search_query_embedding, video_summaries_array)[0]

                top_array = sorted(enumerate(cos_sim), key=lambda x: x[1], reverse=True)
                top_5 = [i for i, v in top_array[:5]]

                #st.write(top_5)

                threshold = 0.7
                similar_results = []

                for x in top_5:
                    if x > threshold:
                        similar_results.append(x)
                
                #  0      1        2               3               4                    5                     6
                # title, id, date of upload, time of upload, full transcript, Paragraph with starts, summary and chapters

                search_index = []

                current_search_index_length = 0
                i = 1
                for search_item in similar_results:
                    x = video_metadatas_array[search_item]
                    current_search_index_length += len(x[6])

                    if current_search_index_length <  6000: # context length limit handling   
                        search_index.append(f"{i}. {x[6]}")
                    i += 1    

                #st.write("\n".join(search_index))    


                def quickchat(search_index):
                    URL = "https://api.openai.com/v1/chat/completions"
                    
                    payload = {
                        "model" : "gpt-3.5-turbo",
                        "temperature" : 0.7,
                        "max_tokens" : 500,
                        "messages" : [
                            {"role":"system", "content": "You are a helpful assistant"},
                            {"role":"user"  , "content": f"From the below query and search context, give a suitable answer along with appropriate video number and chapter timestamp reference. Query: {search_query} \n Search context: \n {search_index}"}
                        ]
                    }

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {chat_key}"
                    }

                    llm_result = requests.post(URL, headers = headers, json = payload).json()
                    generated_content = llm_result['choices'][0]['message']['content']
                    return generated_content

                quick_answer = quickchat("\n".join(search_index))
                st.success(f"**QuickChat Answer:**\n\n{quick_answer}")  
                st.header("Top Results:")  


                for index,q in enumerate(similar_results):
                    x = video_metadatas_array[q]
                    st.header(f"{index+1}. {x[0]}")
                    st.caption(f"Upload time: {x[2]} {x[3]}")
                    st.text(f"Theta Video Link: https://player.thetavideoapi.com/video/{x[1]}")
                    st.components.v1.iframe(f"https://player.thetavideoapi.com/video/{x[1]}")
                    with st.expander("⭐️Summary and Chapters⭐️"):
                        st.write(x[6])
                    with st.expander("Video Transcript"):
                        st.write(x[4])
                    with st.expander("Paragraph Timestamps"):
                        st.write(x[5])

                    st.write("---")


            else:
                st.warning("Please enter a search query")                

