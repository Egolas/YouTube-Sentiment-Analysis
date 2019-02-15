import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk.classify.util as util
from nltk.classify import NaiveBayesClassifier
from nltk.metrics import BigramAssocMeasures
from nltk.classify.scikitlearn import SklearnClassifier
from nltk.collocations import BigramCollocationFinder as BCF
from nltk.probability import FreqDist, ConditionalFreqDist
import itertools
import pickle
from sklearn.naive_bayes import BernoulliNB
import csv
import os, sys, pickle


def features(words, best_words):
    words = set(word_tokenize(words))

    scoreF = BigramAssocMeasures.chi_sq

    # bigram count
    n = 1000

    space = ' '
    bigrams = [space.join(bigram) for bigram in BCF.from_words(words).nbest(scoreF, n)]

    return dict([(word, True) for word in itertools.chain(words, bigrams) if word in best_words])


def fileload(filename):
    with open(filename, encoding='latin-1') as csvfile:
        data = csv.reader(csvfile)
        dataset = []
        for line in data:
            dataset.append(line)
    return dataset


def find_best_words(positiveWords, negativWords, dimention_num):
    # positiveWords = word_tokenize(positiveWords)
    # negativWords = word_tokenize(negativWords)
    space = ' '
    positiveWords = word_tokenize(space.join(positiveWords))
    negativWords = word_tokenize(space.join(negativWords))

    cond_word_fd = ConditionalFreqDist()

    scoreF = BigramAssocMeasures.chi_sq

    posBigrams = BCF.from_words(positiveWords).nbest(scoreF, 5000)
    negBigrams = BCF.from_words(negativWords).nbest(scoreF, 5000)

    pos = positiveWords + posBigrams
    neg = negativWords + negBigrams

    all_words = pos + neg
    word_fd = FreqDist(all_words)
    pos_word_fd = FreqDist(pos)
    neg_word_fd = FreqDist(neg)

    pos_word_count = pos_word_fd.N()
    neg_word_count = neg_word_fd.N()
    total_word_count = pos_word_count + neg_word_count
    word_scores = {}
    for word, freq in word_fd.items():
        pos_score = BigramAssocMeasures.chi_sq(pos_word_fd[word], (freq, pos_word_count), total_word_count)
        neg_score = BigramAssocMeasures.chi_sq(neg_word_fd[word], (freq, neg_word_count), total_word_count)
        word_scores[word] = pos_score + neg_score

    best_vals = sorted(word_scores, key=lambda k: word_scores[k], reverse=True)[:dimention_num]
    return best_vals


def training():
    if os.path.exists('CommentSentimentData/dataset.pkl'):
        with open('CommentSentimentData/dataset.pkl', 'rb') as f:
            dataset = pickle.load(f)
        pos_sen = dataset['pos']
        neg_sen = dataset['neg']

    else:
        dataset = fileload('CommentSentimentData/training.1600000.csv')
        pos_sen = [sen[5] for sen in dataset if sen[0] == '4']
        neg_sen = [sen[5] for sen in dataset if sen[0] == '0']
        dataset_dic = {}
        dataset_dic['pos'] = pos_sen
        dataset_dic['neg'] = neg_sen
        with open('CommentSentimentData/dataset.pkl', 'wb') as f:
            pickle.dump(dataset_dic, f, protocol=pickle.HIGHEST_PROTOCOL)

    if os.path.exists('CommentSentimentData/bestwords.pkl'):
        with open('CommentSentimentData/bestwords.pkl', 'rb') as f:
            best_words = pickle.load(f)
    else:
        best_words = find_best_words(pos_sen, neg_sen, 2000)
        with open('CommentSentimentData/bestwords.pkl', 'wb') as f:
            pickle.dump(best_words, f, protocol=pickle.HIGHEST_PROTOCOL)

    prev = [(features(words, best_words), 'positive') for words in pos_sen]
    nrev = [(features(words, best_words), 'negative') for words in neg_sen]

    pos_set = prev
    neg_set = nrev

    if os.path.exists('CommentSentimentData/classifier.pkl'):
        with open('CommentSentimentData/classifier.pkl', 'rb') as f:
            real_classifier = pickle.load(f)
    else:
        real_classifier = NaiveBayesClassifier.train(prev + nrev)
        with open('CommentSentimentData/classifier.pkl', 'wb') as f:
            pickle.dump(real_classifier, f, protocol=pickle.HIGHEST_PROTOCOL)

    # TO TEST ACCURACY OF CLASSIFIER UNCCOMMENT THE CODE BELOW
    # ACCURACY : 78.1695423855964

    # ncutoff = int(len(nrev) * 3 / 4)
    # pcutoff = int(len(prev) * 3 / 4)
    # train_set = nrev[:ncutoff] + prev[:pcutoff]
    # test_set = nrev[ncutoff:] + prev[pcutoff:]
    # # test_classifier = NaiveBayesClassifier.train(train_set)
    # test_classifier = SklearnClassifier(BernoulliNB()).train(train_set)

    pos_sen = open("CommentSentimentData/positive.txt", 'r', encoding='latin-1').read()
    neg_sen = open("CommentSentimentData/negative.txt", 'r', encoding='latin-1').read()
    prev = [(features(words, best_words), 'positive') for words in pos_sen.split('\n')]
    nrev = [(features(words, best_words), 'negative') for words in neg_sen.split('\n')]
    test_set = nrev + prev

    print("Accuracy is : ", util.accuracy(real_classifier, test_set) * 100)


def main():
    training()


if __name__ == '__main__':
    main()
