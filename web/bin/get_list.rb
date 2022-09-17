#!/usr/bin/env ruby
# coding: utf-8

require 'yaml'
require 'pathname'
require 'date'

require 'google/apis/youtube_v3'

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
      videos << {title: title, video_id: video_id, published_at: detail.snippet.published_at.new_offset(Time.now.getlocal.zone), duration: detail.content_details.duration}
    }

    is_hit = filtered.size < max_results

    break if is_hit or page_token.to_s.empty?
  end

  return videos
end



# ARGV: list.yaml  apikey  listid

listyaml = Pathname(ARGV.first)
list = YAML.load_file(ARGV.first, permitted_classes: [OpenStruct, Symbol, DateTime, Time]) rescue []

tube = Google::Apis::YoutubeV3::YouTubeService.new
tube.key = ARGV[1]

last_name = list.empty? ? /^$/ :  Regexp.new(Regexp.escape(list.first[:title]))

videos = get_until(tube, ARGV[2].to_s, last_name, max_results: 10)
  .sort{|l,r| l[:published_at] <=> r[:published_at]}
  .reverse


puts "Delta: \n#{videos.map{|itm| itm[:title]}.join("\n")}\n------"

yml = (videos + list).to_yaml
#puts yml
File.write(listyaml, yml)
