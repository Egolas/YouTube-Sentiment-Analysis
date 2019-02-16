import requests
import time
import sys
import progress_bar as PB
import os
import time, threading
from queue import Queue
import pickle
import csv
from threading import Lock

proxies = {
    # 'http': 'http://127.0.0.1:2080',
    # 'https': 'http://127.0.0.1:2080'
}

key = ''

COMMENT_API_MORE_PAGE = 'https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&maxResults=100&pageToken={pageToken}&videoId={videoId}&key={key}'
COMMENT_API = 'https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&maxResults=100&videoId={videoId}&key={key}'

CHANNEL_API = 'https://www.googleapis.com/youtube/v3/channels?part=snippet,contentDetails&maxResults=50&id={id}&key={key}'

PLAYLIST_API_MORE_PAGE = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&pageToken={pageToken}&playlistId={playlistId}&key={key}'
PLAYLIST_API = 'https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={playlistId}&key={key}'

VIDEO_API = 'https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&maxResults=5&id={id}&key={key}'

SEARCH_API = 'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=10&type=channel&q={query}&key={key}'

queueDoneLock = threading.Lock()


fieldnames = ['title', 'channelTitle', 'description', 'tags', 'publishedAt', 'viewCount', 'likeCount',
              'dislikeCount', 'favoriteCount', 'commentCount']


def channelRequest(channelId):
    page_info = requests.get(CHANNEL_API.format(id=channelId, key=key), proxies=proxies)
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(CHANNEL_API.format(id=channelId, key=key), proxies=proxies)
    page_info = page_info.json()
    return page_info


def searchRequest(query):
    page_info = requests.get(SEARCH_API.format(query=query, key=key), proxies=proxies)
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(SEARCH_API.format(query=query, key=key), proxies=proxies)
    page_info = page_info.json()
    return page_info


def getVideoIdByChannelId(channelId, queue=None, multithreading=False):
    PB.progress(0, 100)
    page_info = channelRequest(channelId)
    if len(page_info['items']) < 1:
        page_info = searchRequest(channelId)
        id = page_info['items'][0]['id']['channelId']
        page_info = channelRequest(id)
        pass

    playlist_id = page_info['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    page_info = requests.get(PLAYLIST_API.format(playlistId=playlist_id, key=key), proxies=proxies)
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(PLAYLIST_API.format(playlistId=playlist_id, key=key), proxies=proxies)
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
            PLAYLIST_API_MORE_PAGE.format(playlistId=playlist_id, key=key, pageToken=temp['nextPageToken']),
            proxies=proxies)
        while page_info.status_code != 200:
            if page_info.status_code != 429:
                print("Request error")
                sys.exit()

            time.sleep(20)
            page_info = requests.get(
                PLAYLIST_API_MORE_PAGE.format(playlistId=playlist_id, key=key, pageToken=temp['nextPageToken']),
                proxies=proxies)
        page_info = page_info.json()
        for item in page_info['items']:
            curr_num += 1
            if not multithreading:
                video_ids.append(item['snippet']['resourceId']['videoId'])
                PB.progress(curr_num, total_num)
            else:
                queue.put(item['snippet']['resourceId']['videoId'])
                PB.progress(curr_num, total_num)

    if not multithreading:
        return video_ids
    else:
        return


def channelCommentExtract(channel_id, multithreading=False, thread_num=16):
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
        PB.progress(curr_num, total_num)
        pass


def multithreadingCommentExtract(queue):
    while True:
        video_id = queue.get()

        root_path = os.path.abspath('.')
        filename = root_path + '/CommentData/' + str(video_id) + '.dat'

        if os.path.exists(filename):
            queue.task_done()
        else:
            with open(filename, 'wb') as f:
                comments = commentExtract(video_id)
                pickle.dump(comments, f, protocol=pickle.HIGHEST_PROTOCOL)
            queue.task_done()


def multithreadingSaveStastics(channelTitle, statisticsQueue):
    root_path = os.path.abspath('.')
    filename = root_path + '/ChannelStatistics/' + channelTitle + '.csv'
    with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        while True:
            curr_statistics = statisticsQueue.get()

            if curr_statistics == '--thread-end--':
                break

            writer.writerow(curr_statistics)
            statisticsQueue.task_done()



def multithreadingStatisticsExtract(queue, statisticsQueue):
    while True:
        video_id = queue.get()

        if video_id == '--thread-end--':
            break

        curr_statistics = statisticsExtract(video_id)
        snippet = curr_statistics['snippet']
        statistics = curr_statistics['statistics']
        info = snippet
        info.update(statistics)
        info = {dic_key: value for dic_key, value in info.items() if dic_key in fieldnames}

        statisticsQueue.put(info)
        queue.task_done()


def getChannelName(channelId):
    page_info = requests.get(CHANNEL_API.format(id=channelId, key=key), proxies=proxies)
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(CHANNEL_API.format(id=channelId, key=key), proxies=proxies)
    page_info = page_info.json()
    title = page_info['items'][0]['snippet']['title']
    return title


def channelVideoStatisticsExtract(channel_id, multithreading=False, thread_num=32):
    try:
        title = getChannelName(channel_id)
    except Exception:
        title = channel_id

    if multithreading:
        with open('ChannelStatistics/' + title + '.csv', 'w', encoding='utf-8-sig', newline='') as csvfile:
            fieldnames = ['title', 'channelTitle', 'description', 'tags', 'publishedAt', 'viewCount', 'likeCount',
                          'dislikeCount', 'favoriteCount', 'commentCount']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

        queue = Queue(maxsize=thread_num)
        statisticsQueue = Queue(maxsize=128)

        getterThreads = []
        for i in range(thread_num):
            t = threading.Thread(target=multithreadingStatisticsExtract,args=(queue,statisticsQueue,))
            t.daemon = True
            getterThreads.append(t)
            t.start()

        writerThread = threading.Thread(target=multithreadingSaveStastics, args=(title,statisticsQueue,))
        writerThread.start()

        getVideoIdByChannelId(channel_id, queue, True)
        queue.join()
        statisticsQueue.join()

        for i in range(thread_num):
            queue.put('--thread-end--')
        
        statisticsQueue.put('--thread-end--')

        for i in range(thread_num):
            getterThreads[i].join()
        writerThread.join()

    else:
        print('Getting channel video ids...')
        video_ids = getVideoIdByChannelId(channel_id)
        print('Getting all statistics')
        PB.progress(0, 100)
        statistics = []
        curr_num = 0
        total_num = len(video_ids)
        for video_id in video_ids:
            statistics.append(statisticsExtract(video_id))
            curr_num += 1
            PB.progress(curr_num, total_num)

        print('Wring statistics...', end='')
        saveStastics(statistics, title)
        print('done')



def saveStastics(statisticsDict, channelTitle):
    with open('ChannelStatistics/' + channelTitle + '.csv', 'w', encoding='utf-8-sig', newline='') as csvfile:
        fieldnames = ['title', 'channelTitle', 'description', 'tags', 'publishedAt', 'viewCount', 'likeCount',
                      'dislikeCount', 'favoriteCount', 'commentCount']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for video in statisticsDict:
            snippet = video['snippet']
            statistics = video['statistics']
            info = snippet
            info.update(statistics)
            info = {dic_key: value for dic_key, value in info.items() if dic_key in fieldnames}

            writer.writerow(info)


def statisticsExtract(videoId):
    page_info = requests.get(VIDEO_API.format(id=videoId, key=key), proxies=proxies)
    page_info = page_info.json()
    infoDict = {}
    infoDict['snippet'] = page_info['items'][0]['snippet']
    infoDict['statistics'] = page_info['items'][0]['statistics']
    return infoDict


def commentExtract(videoId, count=-1):
    # print("Comments downloading")
    page_info = requests.get(COMMENT_API.format(videoId=videoId, key=key), proxies=proxies)
    while page_info.status_code != 200:
        time.sleep(20)
        page_info = requests.get(COMMENT_API.format(videoId=videoId, key=key), proxies=proxies)

    page_info = page_info.json()

    comments = []
    co = 0
    for i in range(len(page_info['items'])):
        comments.append(page_info['items'][i]['snippet']['topLevelComment']['snippet']['textOriginal'])
        co += 1
        if co == count:
            # PB.progress(co, count)
            return comments

    # PB.progress(co, count)
    # INFINTE SCROLLING
    while 'nextPageToken' in page_info:
        temp = page_info
        page_info = requests.get(
            COMMENT_API_MORE_PAGE.format(videoId=videoId, key=key, pageToken=page_info['nextPageToken']),
            proxies=proxies)

        while page_info.status_code != 200:
            time.sleep(20)
            page_info = requests.get(
                COMMENT_API_MORE_PAGE.format(videoId=videoId, key=key, pageToken=temp['nextPageToken']),
                proxies=proxies)
        page_info = page_info.json()

        for i in range(len(page_info['items'])):
            comments.append(page_info['items'][i]['snippet']['topLevelComment']['snippet']['textOriginal'])
            co += 1
            if co == count:
                # PB.progress(co, count)
                return comments
    #     PB.progress(co, count)
    # PB.progress(count, count)
    # print()
    return comments
