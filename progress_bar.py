import sys


def progress(count, total):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    if count >= total:
        cond = True
    else:
        cond = False

    sys.stdout.write('\r[%s] %s%s' % (bar, percents, '%'))
    sys.stdout.flush()

    if cond == True:
        sys.stdout.write('\n')
