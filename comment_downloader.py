import requests
import time
import sys
import progress_bar as PB
import os
import time, threading
from queue import Queue
import pickle

key = 'AIzaSyBsHts_r9-a-4_xRuWgiuBHLWfe9wWuWfQ'

COMMENT_API_MORE_PAGE = 'https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&maxResults=100&pageToken={pageToken}&videoId={videoId}&key={key}'
COMMENT_API = 'https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&maxResults=100&videoId={videoId}&key={key}'

CHANNEL_API = 'https://www.googleapis.com/youtube/v3/channels?part=contentDetails&maxResults=50&id={id}&key={key}'

PLAYLIST_API_MORE_PAGE = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&pageToken={pageToken}&playlistId={playlistId}&key={key}'
PLAYLIST_API = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={playlistId}&key={key}'

queue = Queue(maxsize=4)

def getVideoIdByChannelId(channelId, queue=None, multithreading=False):
    PB.progress(0, 100)
    page_info = requests.get(CHANNEL_API.format(id=channelId, key=key))
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(CHANNEL_API.format(id=channelId, key=key))
    page_info = page_info.json()
    playlist_id = page_info['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    page_info = requests.get(PLAYLIST_API.format(playlistId=playlist_id, key=key))
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(PLAYLIST_API.format(playlistId=playlist_id, key=key))
    page_info = page_info.json()
    total_num = page_info['pageInfo']['totalResults']
    video_ids = []

    curr_num = 0
    for item in page_info['items']:
        curr_num += 1
        if not multithreading:
            video_ids.append(item['snippet']['resourceId']['videoId'])
            PB.progress(curr_num, total_num)
        else:
            queue.put(item['snippet']['resourceId']['videoId'])
            PB.progress(curr_num, total_num)

    while 'nextPageToken' in page_info:
        temp = page_info
        page_info = requests.get(
            PLAYLIST_API_MORE_PAGE.format(playlistId=playlist_id, key=key, pageToken=temp['nextPageToken']))
        while page_info.status_code != 200:
            if page_info.status_code != 429:
                print("Request error")
                sys.exit()

            time.sleep(20)
            page_info = requests.get(
                PLAYLIST_API_MORE_PAGE.format(playlistId=playlist_id, key=key, pageToken=temp['nextPageToken']))
        page_info = page_info.json()
        for item in page_info['items']:
            curr_num += 1
            if not multithreading:
                video_ids.append(item['snippet']['resourceId']['videoId'])
                PB.progress(curr_num, total_num)
            else:
                queue.put(item['snippet']['resourceId']['videoId'])
                PB.progress(curr_num, total_num)

    print()
    if not multithreading:
        return video_ids
    else:
        return


def channelCommentExtract(channel_id, multithreading=False, thread_num=8):
    if multithreading:
        global queue
        queue = Queue(maxsize=thread_num)
        for i in range(thread_num):
            t = threading.Thread(target=multithreadingCommentExtract)
            t.daemon = True
            t.start()

        getVideoIdByChannelId(channel_id, queue, True)
        queue.join()

    else:
        print('Getting channel video ids...')
        video_ids = getVideoIdByChannelId(channel_id)
        print('Getting all comments')
        PB.progress(0, 100)
        comments = []
        curr_num = 0
        total_num = len(video_ids)
        for video_id in video_ids:
            comments.append(commentExtract(video_id))
            curr_num += 1
            PB.progress(curr_num, total_num)
        PB.progress(curr_num, total_num, cond=True)
        pass


def multithreadingCommentExtract():
    while True:
        video_id = queue.get()

        root_path = os.path.abspath('..')
        filename = root_path + '/CommentData/' + str(video_id) + '.dat'

        if os.path.exists(filename):
            queue.task_done()
        else:
            with open(filename, 'wb') as f:
                comments = commentExtract(video_id)
                pickle.dump(comments, f, protocol=pickle.HIGHEST_PROTOCOL)
            queue.task_done()


def commentExtract(videoId, count=-1):
    # print("Comments downloading")
    page_info = requests.get(COMMENT_API.format(videoId=videoId, key=key))
    while page_info.status_code != 200:
        time.sleep(20)
        page_info = requests.get(COMMENT_API.format(videoId=videoId, key=key))

    page_info = page_info.json()

    comments = []
    co = 0
    for i in range(len(page_info['items'])):
        comments.append(page_info['items'][i]['snippet']['topLevelComment']['snippet']['textOriginal'])
        co += 1
        if co == count:
            # PB.progress(co, count, cond=True)
            return comments

    # PB.progress(co, count)
    # INFINTE SCROLLING
    while 'nextPageToken' in page_info:
        temp = page_info
        page_info = requests.get(
            COMMENT_API_MORE_PAGE.format(videoId=videoId, key=key, pageToken=page_info['nextPageToken']))

        while page_info.status_code != 200:
            time.sleep(20)
            page_info = requests.get(
                COMMENT_API_MORE_PAGE.format(videoId=videoId, key=key, pageToken=temp['nextPageToken']))
        page_info = page_info.json()

        for i in range(len(page_info['items'])):
            comments.append(page_info['items'][i]['snippet']['topLevelComment']['snippet']['textOriginal'])
            co += 1
            if co == count:
                # PB.progress(co, count, cond=True)
                return comments
    #     PB.progress(co, count)
    # PB.progress(count, count, cond=True)
    # print()
    return comments
