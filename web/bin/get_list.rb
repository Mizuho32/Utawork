#!/usr/bin/env ruby
# coding: utf-8

require 'date'

require_relative '../ruby/yt_utils'
require_relative '../ruby/utils'


# ARGV: list.yaml  apikey  listid  list_with_comments.yaml

listyaml = Pathname(ARGV.first)
list = YAML.load_file(ARGV.first, permitted_classes: [OpenStruct, Symbol, DateTime, Time]) rescue []

tube = Google::Apis::YoutubeV3::YouTubeService.new
tube.key = ARGV[1]

last_name = list.empty? ? /^$/ :  Regexp.new(Regexp.escape(list.first[:title]))

videos = YTUtils.get_until(tube, ARGV[2].to_s, last_name, max_results: 10)
  .sort{|l,r| l[:published_at] <=> r[:published_at]}
  .reverse


puts "Delta: \n#{videos.map{|itm| itm[:title]}.join("\n")}\n------"

list = videos + list


# Filter comments or description that looks timestamp
if ARGV[3].nil? then
  $stderr.puts "specify list with comments"
  exit 1
end

id_list = Utils.load_list("", list)
list_with_comments = Utils.load_list(ARGV[3])
time_reg = /(?:\d+:)+\d+/

no_seg_ids = list.select{|item| !item[:has_segments]}.map{|item| item[:video_id].to_sym }
no_seg_ids.each{|video_id|
  item = list_with_comments[video_id]
  next if item.nil?

  text = item[:comments].join("\n") + "\n" + item[:description]
  timestamps = text.each_line
    .select{|line| line =~ time_reg}
    .map{|line|
       startend = line.scan(time_reg).map{|timestamp|
         timestamp.split(?:).reverse.each_with_index.map{|time, i| time.to_i * 60**i}.sum.to_f
       }
       other = line.split(time_reg).reject(&:empty?).map(&:strip)
       (startend + other).join("\t")
    }

  if !timestamps.empty? then
    puts video_id, timestamps, "---"
    Utils.save_segments(video_id.to_s, timestamps.join("\n"))
    id_list[video_id][:has_segments] = true
  end
}

yml = list.to_yaml

#puts yml
File.write(listyaml, yml)

