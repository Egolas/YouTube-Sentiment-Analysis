import sys


def progress(count, total, msg=None):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    if count >= total:
        cond = True
    else:
        cond = False
    if msg is None:
        sys.stdout.write('\r[%s] %s%s' % (bar, percents, '%'))
        sys.stdout.flush()
    else:
        sys.stdout.write('\r[%s] %s%s, %s' % (bar, percents, '%', msg))
        sys.stdout.flush()

    if cond == True:
        sys.stdout.write('\n')
