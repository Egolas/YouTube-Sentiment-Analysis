import csv
import os
import re
from wordcloud import WordCloud
from collections import Counter
import matplotlib.pyplot as plt
from scipy.misc import imread
from wordcloud import WordCloud, ImageColorGenerator

def get_filenames(path):
    file_names = []
    for x in os.listdir(path):
        # print(x)
        y = os.path.join(path,x)
        if os.path.isfile(y):
            file_path = os.path.split(y)
            lists = file_path[1].split('.') #分割出文件与文件扩展名  
            file_ext = lists[-1] #取出后缀名(列表切片操作)
            img_ext = ['csv']
            if file_ext in img_ext:
                file_name = ' '.join(lists[:-1])
                file_names.append(file_name)
    return file_names

def main():
    path = 'ChannelStatistics'
    file_names = get_filenames(path)

    for name in file_names:
        if name[0] == '#':
            continue

        tag_dict = {}
        with open('ChannelStatistics/' + '#tag_statistics_' + name +  '.csv', 'w', encoding='utf-8-sig', newline='') as csvfile:
            fieldnames = ['tags', 'viewCount']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            with open(path+ '/' + name + '.csv', 'r', encoding='utf-8-sig',newline='') as csvfile:
                csv_reader = csv.DictReader(csvfile)
                for row in csv_reader:
                    viewCount = int(row['viewCount'])
                    try:
                        tags = eval(row['tags'])
                    except:
                        tags = list(row['tags'])
                
                    for tag in tags:
                        if tag in tag_dict:
                            tag_dict[tag] += viewCount
                        else:
                            tag_dict[tag] = viewCount
                    pass
            
            for tag, viewCount in tag_dict.items():
                writer.writerow({fieldnames[0]:tag, fieldnames[1]:viewCount})
            
    pass

def showFancySentiment(file_name):
    tag_dict = {}

    with open('ChannelStatistics/' + file_name +  '.csv','r', encoding='utf-8-sig',newline='') as csvfile:
            fieldnames = ['tags', 'viewCount']
            csv_reader = csv.DictReader(csvfile)
            for row in csv_reader:
                viewCount = int(row['viewCount'])
                tag = row['tags']
                tag_dict[tag] = viewCount
                pass
    color_mask = imread("china_map.png")

    wc = WordCloud(
        #设置字体，不指定就会出现乱码，注意字体路径
        font_path="simkai.ttf",
        #font_path=path.join(d,'simsun.ttc'),
        #设置背景色
        background_color='white',
        #词云形状
        mask=color_mask,
        #允许最大词汇
        max_words=2000,
        #最大号字体
        max_font_size=60,
        scale=32
    )
    wc.generate_from_frequencies(Counter(tag_dict))
    image_colors = ImageColorGenerator(color_mask)
    wc.recolor(color_func=image_colors)
    wc.to_file("wcloud_" + file_name+ ".jpg")

    # plt.imshow(wc,interpolation="bilinear") # 显示词云
    # plt.axis('off') # 关闭坐标轴
    # plt.show()
                
def batchWordCloud(path):
    path = 'ChannelStatistics'
    file_names = get_filenames(path)

    for name in file_names:
        if name[0] != '#':
            continue
        
        showFancySentiment(name)
        


if __name__ == '__main__':
    # showFancySentiment('#tag_statistics_CCTV中国中央电视台')
    batchWordCloud('ChannelStatistics')
    # main()
