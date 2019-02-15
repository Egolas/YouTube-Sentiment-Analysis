import training_classifier as tcl
import os.path
from statistics import mode
from nltk.classify import ClassifierI
from nltk.tokenize import word_tokenize
from nltk.metrics import BigramAssocMeasures
from nltk.classify.scikitlearn import SklearnClassifier
from nltk.collocations import BigramCollocationFinder as BCF
from nltk.probability import FreqDist, ConditionalFreqDist
import itertools
from sklearn.naive_bayes import BernoulliNB
import os, pickle


def features(words, best_words):
    words = set(word_tokenize(words))

    scoreF = BigramAssocMeasures.chi_sq

    # bigram count
    n = 1000

    space = ' '
    bigrams = [space.join(bigram) for bigram in BCF.from_words(words).nbest(scoreF, n)]

    return dict([(word, True) for word in itertools.chain(words, bigrams) if word in best_words])


class VoteClassifier(ClassifierI):
    def __init__(self, *classifiers):
        self.__classifiers = classifiers

    def classify(self, comments):
        votes = []
        for c in self.__classifiers:
            v = c.classify(comments)
            votes.append(v)
        con = mode(votes)

        choice_votes = votes.count(mode(votes))
        conf = (1.0 * choice_votes) / len(votes)

        return con, conf


def sentiment(comments):
    if not os.path.isfile('CommentSentimentData/classifier.pkl'):
        tcl.training()

    fl = open('CommentSentimentData/classifier.pkl', 'rb')
    classifier = pickle.load(fl)
    fl.close()

    with open('CommentSentimentData/bestwords.pkl', 'rb') as f:
        best_words = pickle.load(f)

    pos = 0
    neg = 0
    for words in comments:
        comment = features(words, best_words)
        sentiment_value, confidence = VoteClassifier(classifier).classify(comment)
        if sentiment_value == 'positive':  # and confidence * 100 >= 60:
            pos += 1
        else:
            neg += 1

    print("Positive sentiment : ", (pos * 100.0 / len(comments)))
    print("Negative sentiment : ", (neg * 100.0 / len(comments)))


def find_best_words(positiveWords, negativWords, dimention_num):
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


def train(dataset):
    pos_sen = dataset['pos']
    neg_sen = dataset['neg']

    space = ' '
    positiveWords = word_tokenize(space.join(pos_sen))
    negativWords = word_tokenize(space.join(neg_sen))


    if os.path.exists('CommentSentimentData/bestwords.pkl'):
        with open('CommentSentimentData/bestwords.pkl', 'rb') as f:
            best_words = pickle.load(f)
    else:
        best_words = find_best_words(positiveWords, negativWords, 2000)
        with open('CommentSentimentData/bestwords.pkl', 'wb') as f:
            pickle.dump(best_words, f, protocol=pickle.HIGHEST_PROTOCOL)

    prev = [(features(words, best_words), 'positive') for words in pos_sen]
    nrev = [(features(words, best_words), 'negative') for words in neg_sen]

    if os.path.exists('CommentSentimentData/classifier.pkl'):
        with open('classifier.pkl', 'rb') as f:
            classifier = pickle.load(f)
    else:
        classifier = SklearnClassifier(BernoulliNB()).train(prev + nrev)
        with open('CommentSentimentData/classifier.pkl', 'wb') as f:
            pickle.dump(classifier, f, protocol=pickle.HIGHEST_PROTOCOL)


def train_processed(dataset):
    pos_sen = dataset['pos']
    neg_sen = dataset['neg']

    if os.path.exists('CommentSentimentData/bestwords.pkl'):
        with open('CommentSentimentData/bestwords.pkl', 'rb') as f:
            best_words = pickle.load(f)
    else:
        best_words = find_best_words(pos_sen, neg_sen, 2000)
        with open('CommentSentimentData/bestwords.pkl', 'wb') as f:
            pickle.dump(best_words, f, protocol=pickle.HIGHEST_PROTOCOL)

    prev = [(features(words, best_words), 'positive') for words in pos_sen]
    nrev = [(features(words, best_words), 'negative') for words in neg_sen]

    if os.path.exists('CommentSentimentData/classifier.pkl'):
        with open('CommentSentimentData/classifier.pkl', 'rb') as f:
            classifier = pickle.load(f)
    else:
        classifier = SklearnClassifier(BernoulliNB()).train(prev + nrev)
        with open('CommentSentimentData/classifier.pkl', 'wb') as f:
            pickle.dump(classifier, f, protocol=pickle.HIGHEST_PROTOCOL)
