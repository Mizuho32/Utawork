require 'yaml'
require 'pathname'
require 'date'

require 'google/apis/youtube_v3'

module YTUtils
extend self

  def get_video_details(youtube, ids, max_results = 10, part: "id,snippet,contentDetails")
    ids = [ids] if ids.is_a? String

    all_items = ids.each_slice(max_results).inject([]){|items, ids_sub|
      items += youtube.list_videos(part, id: ids_sub.join(",")).items
      items
    }
    return all_items
  end

  def get_until(tube, id, title_reg, video_id_reg=/^$/, max_results: 5)
    page_token = nil
    videos = []

    loop do
      res = tube.list_playlist_items('snippet,contentDetails', playlist_id: id.to_s, max_results: max_results, page_token: page_token)
      page_token = res.next_page_token

      filtered = res.items.map{|itm|
        title, video_id = itm.snippet.title, itm.content_details.video_id

        [title, video_id]
      }.take_while{|(title, video_id)|
        not (title_reg =~ title or video_id_reg =~ video_id)
      }.each{|(title, video_id)|
        next if title == "Private video" || title == "Deleted video"
        puts title
        detail = get_video_details(tube, video_id).first
        videos << {title: title, video_id: video_id, published_at: detail.snippet.published_at.new_offset(Time.now.getlocal.zone), duration: detail.content_details.duration} if not detail.nil?
      }

      is_hit = filtered.size < max_results

      break if is_hit or page_token.to_s.empty?
    end

    return videos
  end

  def get_comments(tube, videoId)
    tube.list_comment_threads('snippet', video_id: videoId, order: "relevance")
      .items.map{|item|
        item.snippet.top_level_comment.snippet.text_original
      }
  end

end
