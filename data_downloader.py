import requests
import time
import sys
import progress_bar as PB
import os
import time, threading
from queue import Queue
import pickle
import csv
import time
from threading import Lock

proxies = {
    'http': 'http://127.0.0.1:2080',
    'https': 'http://127.0.0.1:2080'
}

key = ''

commentDefaultPayload = {'key': key, 'maxResults': 100, 'part': 'snippet'}
COMMENT_API = 'https://www.googleapis.com/youtube/v3/commentThreads'

channelDefaultPayload = {'key': key, 'maxResults': 50, 'part': 'snippet,statistics,contentDetails'}
CHANNEL_API = 'https://www.googleapis.com/youtube/v3/channels'

playlistDefaultPayload = {'key': key, 'maxResults': 50, 'part': 'snippet'}
PLAYLIST_API = 'https://www.googleapis.com/youtube/v3/playlistItems'

videoDefaultPayload = {'key': key, 'part': 'snippet,contentDetails,topicDetails,statistics', 'maxResults': 5}
VIDEO_API = 'https://www.googleapis.com/youtube/v3/videos'

searchDefaultPayload = {'key': key, 'part': 'snippet', 'maxResults': 50}
SEARCH_API = 'https://www.googleapis.com/youtube/v3/search'

fieldnames = ['title', 'channelTitle', 'description', 'tags', 'publishedAt', 'viewCount', 'likeCount',
              'dislikeCount', 'favoriteCount', 'commentCount']

def channelRequest(channelId):
    payload = channelDefaultPayload
    payload['id'] = channelId
    page_info = requests.get(CHANNEL_API, params=payload, proxies=proxies)
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(CHANNEL_API, params=payload, proxies=proxies)
    page_info = page_info.json()
    return page_info


def searchRequest(query, type, pageToken=None, publishedAfter=None, publishedBefore=None):
    if pageToken == None:
        payload = searchDefaultPayload
        payload['query'] = query
        payload['type'] = type
        payload['publishedAfter'] = publishedAfter
        payload['publishedBefore'] = publishedBefore
        page_info = requests.get(SEARCH_API, params=payload,
                                 proxies=proxies)
        while page_info.status_code != 200:
            if page_info.status_code != 429:
                print("Request error")
                sys.exit()

            time.sleep(20)
            page_info = requests.get(SEARCH_API, params=payload,
                                     proxies=proxies)
        page_info = page_info.json()
        return page_info
    else:
        payload = searchDefaultPayload
        payload['query'] = query
        payload['type'] = type
        payload['pageToken'] = pageToken
        payload['publishedAfter'] = publishedAfter
        payload['publishedBefore'] = publishedBefore
        page_info = requests.get(SEARCH_API, params=payload,
                                 proxies=proxies)
        while page_info.status_code != 200:
            if page_info.status_code != 429:
                print("Request error")
                sys.exit()

            time.sleep(20)
            page_info = requests.get(SEARCH_API, params=payload,
                                     proxies=proxies)
        page_info = page_info.json()
        return page_info


def getSearchResultIds(query, type, totalNum=500, publishedAfter=None, publishedBefore=None, queue=None,
                       multithreading=False):
    print('Getting ids...')
    PB.progress(0, 100)

    videoIds = []
    page_info = searchRequest(query, type)
    totalResultNum = page_info['pageInfo']['totalResults']

    currNum = 0
    searchedNum = 0
    for item in page_info['items']:
        searchedNum += 1

        id = item['id']['videoId']
        if multithreading is True:
            queue.put(id)
        else:
            videoIds.append(id)
        currNum += 1
        PB.progress(currNum, min(totalResultNum, totalNum),
                    msg="Curr num {:d}, serched {:d}, objective num {:d}, total result {:d}".format(currNum,
                                                                                                    searchedNum,
                                                                                                    totalNum,
                                                                                                    totalResultNum))

        if currNum >= min(totalResultNum, totalNum):
            print('Overflow')
            break

    while 'nextPageToken' in page_info and currNum < min(totalResultNum, totalNum):
        page_info = searchRequest(query, type, page_info['nextPageToken'])
        for item in page_info['items']:
            searchedNum += 1

            id = item['id']['videoId']
            if multithreading is True:
                queue.put(id)
            else:
                videoIds.append(id)
            currNum += 1
            PB.progress(currNum, min(totalResultNum, totalNum),
                        msg="Curr num {:d}, serched {:d}, objective num {:d}, total result {:d}".format(currNum,
                                                                                                        searchedNum,
                                                                                                        totalNum,
                                                                                                        totalResultNum))
            if currNum >= min(totalResultNum, totalNum):
                print('Overflow')
                break

    print()

    if 'nextPageToken' not in page_info and currNum < min(totalResultNum, totalNum):
        print("No more video matched conditions.")

    print("Id getting procedure done.")
    return videoIds


def getChannelStatistics(channel_id):
    c_statistics = {}
    try:
        page_info = channelRequest(channel_id)['items'][0]
        c_statistics['channel_title'] = page_info['snippet']['title']
        c_statistics['channel_subscriberCount'] = page_info['statistics']['subscriberCount']
        c_statistics['channel_registeredAt'] = page_info['snippet']['publishedAt']
        c_statistics['channel_viewCount'] = page_info['statistics']['viewCount']
    except Exception as err:
        c_statistics['channel_title'] = '! Error: channel isn\'t accessible'
        pass

    return c_statistics


# only for type is 'video', others haven't implemented
def getSearchResultStatistics(query, type, totalNum=500, withoutTopics=None, publishedAfter=None, publishedBefore=None,
                              multithreading=False, thread_num=32):
    field_names = ['link', 'title', 'topicCategories', 'description', 'tags', 'publishedAt',
                   'viewCount', 'likeCount',
                   'dislikeCount', 'favoriteCount', 'commentCount', 'channel_title', 'channel_subscriberCount',
                   'channel_registeredAt', 'channel_viewCount']

    if multithreading:
        with open('SearchStatistics/' + query + '.csv', 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            writer.writeheader()

        queue = Queue(maxsize=thread_num)
        statisticsQueue = Queue(maxsize=128)

        getterThreads = []
        for i in range(thread_num):
            t = threading.Thread(target=multithreadingGetSearchResultStatistics, args=(queue, statisticsQueue,))
            getterThreads.append(t)
            t.start()
        if withoutTopics is None:
            writerThread = threading.Thread(target=multithreadingSaveSearchStastics, args=(query, statisticsQueue,))
        else:
            writerThread = threading.Thread(target=multithreadingSaveSearchStastics,
                                            args=(query, statisticsQueue, withoutTopics,))
        writerThread.start()

        getSearchResultIds(query, type, totalNum, publishedAfter=publishedAfter, publishedBefore=publishedBefore,
                           queue=queue, multithreading=True)
        queue.join()
        statisticsQueue.join()

        for i in range(thread_num):
            queue.put('--thread-end--')

        statisticsQueue.put('--thread-end--')

        for i in range(thread_num):
            getterThreads[i].join()
        writerThread.join()

    else:
        videoIds = getSearchResultIds(query, type, totalNum, publishedAfter=publishedAfter,
                                      publishedBefore=publishedBefore)

        statisticsList = []

        print('Getting statistics...')
        PB.progress(0, 100)
        totalNum = len(videoIds)

        for i, video_id in enumerate(videoIds):
            PB.progress(i + 1, totalNum)
            link = r'https://www.youtube.com/watch?v=' + video_id
            curr_statistics = statisticsExtract(video_id)
            snippet = curr_statistics['snippet']
            channelId = snippet['channelId']
            statistics = curr_statistics['statistics']

            info = snippet
            info['link'] = link
            info.update(statistics)

            if 'topicDetails' in curr_statistics:
                info.update(curr_statistics['topicDetails'])

            if 'topicCategories' in info:
                info['topicCategories'] = [x.split('/')[-1] for x in info['topicCategories']]

            channel_statistics = getChannelStatistics(info['channelId'])
            info.update(channel_statistics)

            info = {dic_key: value for dic_key, value in info.items() if dic_key in field_names}
            statisticsList.append(info)

        with open('SearchStatistics/' + query + '.csv', 'w', encoding='utf-8-sig', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()

            for info in statisticsList:
                writer.writerow(info)


def getVideoIdByChannelId(channelId, queue=None, multithreading=False):
    PB.progress(0, 100)
    page_info = channelRequest(channelId)
    if len(page_info['items']) < 1:
        page_info = searchRequest(channelId)
        id = page_info['items'][0]['id']['channelId']
        page_info = channelRequest(id)
        pass

    playlist_id = page_info['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    payload = playlistDefaultPayload
    payload['playlistId'] = playlist_id
    page_info = requests.get(PLAYLIST_API, params=payload, proxies=proxies)
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(PLAYLIST_API, params=payload, proxies=proxies)
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

        payload = playlistDefaultPayload
        payload['playlistId'] = playlist_id
        payload['nextPageToken'] = temp['nextPageToken']

        page_info = requests.get(
            PLAYLIST_API, params=payload, proxies=proxies)
        while page_info.status_code != 200:
            if page_info.status_code != 429:
                print("Request error")
                sys.exit()

            time.sleep(20)
            page_info = requests.get(
                PLAYLIST_API, params=payload, proxies=proxies)
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


def multithreadingGetSearchResultStatistics(queue, statisticsQueue):
    field_names = ['link', 'title', 'topicCategories', 'description', 'tags', 'publishedAt',
                   'viewCount', 'likeCount',
                   'dislikeCount', 'favoriteCount', 'commentCount', 'channel_title', 'channel_subscriberCount',
                   'channel_registeredAt', 'channel_viewCount']

    while True:
        video_id = queue.get()

        if video_id == '--thread-end--':
            queue.task_done()
            print("Received end thread signal.")
            break

        link = r'https://www.youtube.com/watch?v=' + video_id
        curr_statistics = statisticsExtract(video_id)
        snippet = curr_statistics['snippet']
        channelId = snippet['channelId']
        statistics = curr_statistics['statistics']

        info = snippet
        info['link'] = link
        info.update(statistics)

        if 'topicDetails' in curr_statistics:
            info.update(curr_statistics['topicDetails'])

        if 'topicCategories' in info:
            info['topicCategories'] = [x.split('/')[-1] for x in info['topicCategories']]

        try:
            channel_statistics = getChannelStatistics(info['channelId'])
            info.update(channel_statistics)
        except:
            pass

        info = {dic_key: value for dic_key, value in info.items() if dic_key in field_names}
        statisticsQueue.put(info)
        queue.task_done()

    # print('Getter thread ended.')


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


def multithreadingSaveSearchStastics(searchKeyWords, statisticsQueue, withoutTopics=None):
    field_names = ['link', 'title', 'topicCategories', 'description', 'tags', 'publishedAt',
                   'viewCount', 'likeCount',
                   'dislikeCount', 'favoriteCount', 'commentCount', 'channel_title', 'channel_subscriberCount',
                   'channel_registeredAt', 'channel_viewCount']

    root_path = os.path.abspath('.')
    filename = root_path + '/SearchStatistics/' + searchKeyWords + '.csv'
    with open(filename, 'a', encoding='utf-8-sig', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=field_names)

        while True:
            curr_statistics = statisticsQueue.get()

            if curr_statistics == '--thread-end--':
                break

            if withoutTopics is None:
                writer.writerow(curr_statistics)
                statisticsQueue.task_done()
            else:
                if 'topicCategories' in curr_statistics and len(
                        [topic for topic in curr_statistics['topicCategories'] if topic in withoutTopics]) > 0:
                    statisticsQueue.task_done()
                    continue

                writer.writerow(curr_statistics)
                statisticsQueue.task_done()

    print('Writer thread ended.')


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
            queue.task_done()
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
    payload = channelDefaultPayload
    payload['id'] = channelId
    page_info = requests.get(CHANNEL_API, params=payload, proxies=proxies)
    while page_info.status_code != 200:
        if page_info.status_code != 429:
            print("Request error")
            sys.exit()

        time.sleep(20)
        page_info = requests.get(CHANNEL_API, params=payload, proxies=proxies)
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
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

        queue = Queue(maxsize=thread_num)
        statisticsQueue = Queue(maxsize=128)

        getterThreads = []
        for i in range(thread_num):
            t = threading.Thread(target=multithreadingStatisticsExtract, args=(queue, statisticsQueue,))
            t.daemon = True
            getterThreads.append(t)
            t.start()

        writerThread = threading.Thread(target=multithreadingSaveStastics, args=(title, statisticsQueue,))
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
    payload = videoDefaultPayload
    payload['id'] = videoId
    page_info = requests.get(VIDEO_API, params=payload, proxies=proxies)
    page_info = page_info.json()

    page_info_item = page_info['items'][0]
    infoDict = {}
    infoDict['snippet'] = page_info_item['snippet']
    infoDict['statistics'] = page_info_item['statistics']
    if 'topicDetails' in page_info_item:
        infoDict['topicDetails'] = page_info_item['topicDetails']
    return infoDict


def commentExtract(videoId, count=-1):
    # print("Comments downloading")
    payload = commentDefaultPayload
    payload['videoId'] = videoId
    page_info = requests.get(COMMENT_API, params=payload, proxies=proxies)
    while page_info.status_code != 200:
        time.sleep(20)
        page_info = requests.get(COMMENT_API, params=payload, proxies=proxies)

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
        payload = commentDefaultPayload
        payload['videoId'] = videoId
        payload['nextPageToken'] = temp['nextPageToken']
        page_info = requests.get(
            COMMENT_API, params=payload, proxies=proxies)

        while page_info.status_code != 200:
            time.sleep(20)
            page_info = requests.get(
                COMMENT_API, params=payload, proxies=proxies)
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
