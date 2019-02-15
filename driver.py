import comment_downloader as CD
import fancySentiment as FS

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
	channel_id = 'UCDsO-0Yo5zpJk575nKXgMVA'
	CD.channelCommentExtract(channel_id, multithreading=True)



if __name__ == '__main__':
	main()
