#!/usr/bin/env ruby
# coding: utf-8

require 'date'

require_relative '../ruby/yt_utils'


# ARGV: list.yaml  apikey  listid  update_comment_range
# update_comment_range: 0 is latest one in list.yaml (e.g. 0..-1)


listyaml = Pathname(ARGV.first)
list = YAML.load_file(ARGV.first, permitted_classes: [OpenStruct, Symbol, DateTime, Time]) rescue []

tube = Google::Apis::YoutubeV3::YouTubeService.new
tube.key = ARGV[1]

last_name = list.empty? ? /^$/ :  Regexp.new(Regexp.escape(list[0][:title]))

videos = YTUtils.get_until(tube, ARGV[2].to_s, last_name, max_results: 10)
  .sort{|l,r| l[:published_at] <=> r[:published_at]}
  .reverse


puts "Delta: \n#{videos.map{|itm| itm[:title]}.join("\n")}\n------"

total_list = list + videos
File.write(listyaml, total_list.to_yaml)

# get comments
if ARGV[3] then
  update_comment_range = eval(ARGV[3])

  total_list[update_comment_range].map{|video|
    puts "Process #{video[:title]}"
    video[:comments] = YTUtils.get_comments(tube, video[:video_id])
    video
  }
end

File.write(listyaml, total_list.to_yaml)
