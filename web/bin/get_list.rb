#!/usr/bin/env ruby
# coding: utf-8

require 'date'

require_relative '../ruby/yt_utils'


# ARGV: list.yaml  apikey  listid

listyaml = Pathname(ARGV.first)
list = YAML.load_file(ARGV.first, permitted_classes: [OpenStruct, Symbol, DateTime, Time]) rescue []

tube = Google::Apis::YoutubeV3::YouTubeService.new
tube.key = ARGV[1]

last_name = list.empty? ? /^$/ :  Regexp.new(Regexp.escape(list.first[:title]))

videos = YTUtils.get_until(tube, ARGV[2].to_s, last_name, max_results: 10)
  .sort{|l,r| l[:published_at] <=> r[:published_at]}
  .reverse


puts "Delta: \n#{videos.map{|itm| itm[:title]}.join("\n")}\n------"

yml = (videos + list).to_yaml
#puts yml
File.write(listyaml, yml)
