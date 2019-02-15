import sys

# edited, original version not work on my console
def progress(count, total, cond=False):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    if cond is False:
        print('\r[%s] %s%s' % (bar, percents, '%'), end='')
        sys.stdout.flush()

    else:
        print('\r[%s] %s%s' % (bar, percents, '%'))
