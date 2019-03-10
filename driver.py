import data_downloader as DD
import fancySentiment as FS
import sentimentYouTube as SYT
import os
import pickle
import csv
import sys


def get_file_name(file_dir):
    L = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if os.path.splitext(file)[1] == '.dat':
                L.append(os.path.join(root, file))

    return L


def fileload(filename):
    with open(filename, encoding='latin-1') as csvfile:
        data = csv.reader(csvfile)
        dataset = []
        for line in data:
            dataset.append(line)
    return dataset


def sentimentProcess():
    # dataset_dic shall be a dic with two keys: 'pos', 'neg', the values of keys above shall be the list of samples,
    # where each of the sample shall be a tuple of text

    if os.path.exists('dataset.pkl'):
        with open('dataset.pkl', 'rb') as f:
            dataset_dic = pickle.load(f)
    else:
        dataset = fileload('training.1600000.csv')
        pos_sen = [sen[5] for sen in dataset if sen[0] == '4']
        neg_sen = [sen[5] for sen in dataset if sen[0] == '0']
        dataset_dic = {}
        dataset_dic['pos'] = pos_sen
        dataset_dic['neg'] = neg_sen
        with open('dataset.pkl', 'wb') as f:
            pickle.dump(dataset_dic, f, protocol=pickle.HIGHEST_PROTOCOL)

    file_names = get_file_name('../CommentData/')
    comments = []
    for file_name in file_names:
        with open('../CommentData/' + file_name, 'rb') as f:
            comments.extend(pickle.load(f))

    SYT.train(dataset_dic)
    SYT.sentiment(comments)


def main():
    # # EXAMPLE videoID = 'tCXGJQYZ9JA'
    # videoId = input("Enter the videoID : ")
    # # Fetch the number of comments
    # # if count = -1, fetch all comments
    # count = int(input("Enter the no. of comment to extract : "))
    #
    # comments = DD.commentExtract(videoId, count)
    #
    # FS.fancySentiment(comments)

    # channel_id = ''
    # # DD.channelCommentExtract(channel_id, multithreading=False)
    # print('dealing with', channel_id)
    # DD.channelVideoStatisticsExtract(channel_id, multithreading=True)

    withoutTopics = ['Music', 'Politics', 'Film', 'Military', 'Sport']
    DD.getSearchResultStatistics("chinese", "video", totalNum=1000,  multithreading=True, withoutTopics=withoutTopics)

if __name__ == '__main__':
    main()
