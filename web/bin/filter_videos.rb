#!/usr/bin/env ruby
# coding: utf-8

require 'date'

require_relative '../ruby/yt_utils'


# ARGV: list.yaml  apikey  listid  update_comment_range  list2.yaml
# 3: update_comment_range: 0 is latest one in list.yaml (e.g. 0..-1), optional
# 4: list2.yaml: print list with tag info [yet impl]


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

  if update_comment_range.is_a? Range then
    total_list[update_comment_range].map!{|video|
      print "Process #{video[:title]}"

      video[:comments] = YTUtils.get_comments(tube, video[:video_id]) if !video[:comments]
      video[:description] = YTUtils.get_video_details(tube, video[:video_id], part: "id,snippet")
        .first.snippet.description if !video[:description]

      puts "  Done."
      video
    }
    File.write(listyaml, total_list.to_yaml)
  end
end


#if ARGV[4] then
#  total_list = Hash[ total_list.map{|item| [item[:video_id].to_sym, item]} ]
#
#  require_relative '../ruby/utils'
#  puts Utils.load_list(ARGV[4])
#    .select{|k, v| not v[:comments].join.include?("sheet") }
#    .map{|k, v| total_list[v[:video_id].to_sym]}
#    .compact
#    .select{|item| item[:has_tags] }
#    .map{|item| [item[:title],item[:video_id]] }
#    .map(&:to_csv)
#    .join
#end
