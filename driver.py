import comment_downloader as CD
import fancySentiment as FS
import sentimentYouTube as SYT
import os
import pickle
import csv


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
    # comments = CD.commentExtract(videoId, count)
    #
    # FS.fancySentiment(comments)
    ids = ['李子柒',
            'Li Ziqi Style',
            '滇西小哥',
            '乡间小蓉',
            '酒鬼小莉',
            '山药视频',
            '华农兄弟',
            '野食小哥',
            '龙梅梅L',
            '二米炊烟',
            '中国日报CHINADAILY官方频道OFFICIAL CHANNEL',
            'CGTN',
            'CCTV中国中央电视台',
            'People\'s Daily, China 人民日报',
            'SMG上海电视台官方频道 SMG Shanghai TV Official Channel',
            'ChineseCultureCtr',
           ]

    for channel_id in ids:
        # CD.channelCommentExtract(channel_id, multithreading=False)
        print('dealing with', channel_id)
        CD.channelVideoStatisticsExtract(channel_id, multithreading=True)


if __name__ == '__main__':
    main()
