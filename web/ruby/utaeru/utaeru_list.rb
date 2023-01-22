#!/usr/bin/env ruby
# coding: utf-8

require 'date'
require 'csv'
require 'yaml'
require 'pathname'

require_relative "song"

module Utaeru
  extend self

  def load_songs(path, title_exclude=nil, hash_mode = true)
    listyaml = Pathname(path)
    list = YAML.load_file(path, permitted_classes: [OpenStruct, Symbol, DateTime, Time]) rescue []
    data_dir = listyaml.parent

    # filter by title and tags.csv file
    return list.select{|elm|
      vid = elm[:video_id]
      (not not title_exclude.nil? or (elm[:title] !~ title_exclude))  and (data_dir / vid / "tags.csv").exist?
    }.map{|elm|
      song_artist = CSV.read(data_dir / elm[:video_id] / "tags.csv")
        .select{|_,_, name, artist|
          !name.empty? && !artist.empty?
        }.map{|start_time, end_time, name, artist|
          if hash_mode then
            {name: name, artist: artist}
          else
            Song.new(name, artist, elm[:video_id], start_time, end_time)
          end
        }
    }.flatten
  end

  def clarify(str, equals)
    str.gsub!("　", " ")
    equals.each{|before, after|
      str.gsub!(before, after)
    }

    return str
  end

  # equals: {before: after}
  def beautify(songs, equals, hash_mode = true)
    song_to_split = []
    artist_to_split = []

    song_splitted = songs.map{|elm|
      tmp = elm.map{|k,v|
        [k, clarify(v, equals).strip]
      }
      if hash_mode then
        Hash[tmp]
      else
        Song[tmp]
      end
    }.reject{|elm|
      matched = elm[:name].match(/[(（][^)）]+[)）]/)
      song_to_split << elm if matched

      matched
    }

    song_to_split.each{|elm|
      m = elm[:name].match(/([^(（]+)[(（]([^)）]+)[)）]/)

      if not m.nil? then
        (1..2).each{|idx|
          song = if hash_mode then
            {name: m[idx].strip, artist: elm[:artist]}
          else
            Song.new(m[idx].strip, elm[:artist], elm[:video_id], elm[:start_time], elm[:end_time])
          end

          song_splitted << song
        }
      end
    }

    artist_splitted = song_splitted.reject{|elm|
      matched = elm[:artist].match(/[,、]/)
      artist_to_split << elm if matched

      matched
    }

    artist_to_split.each{|elm|
      elm[:artist].split(/[,、]/).each{|artist|
          song = if hash_mode then
            {name: elm[:name], artist: artist.strip}
          else
            Song.new(elm[:name], artist.strip, elm[:video_id], elm[:start_time], elm[:end_time])
          end
        artist_splitted << song
      }
    }
    
    return artist_splitted
  end

  def name_uniqnize(songs)
    songs
      .group_by{|elm| elm[:name].gsub(/\s+/, "").downcase}
      .map{|_, eqls|
        name, name_freq = eqls.map{|elm| elm[:name]}
          .group_by{|name| name}.map{|name, name_eqls| [name, name_eqls.size]}
          .sort{|(lname, lfreq),(rname,rfreq)| lfreq <=> rfreq}.reverse.first

        artist, artist_freq = eqls.map{|elm| elm[:artist]}
          .group_by{|artist| artist}.map{|artist, artist_eqls| [artist, artist_eqls.size]}
          .sort{|(lartist, lfreq),(rartist,rfreq)| lfreq <=> rfreq}.reverse.first

        {name: name, artist: artist}
      }
  end

  def group_by_artist(songs, hash_mode = true)
    Hash[songs
      .group_by{|elm| elm[:artist].gsub(/\s+/, "").downcase}
      .map{|_, eqls|
        artist, artist_freq = eqls.map{|elm| elm[:artist]}
          .group_by{|artist| artist}.map{|artist, artist_eqls| [artist, artist_eqls.size]}
          .sort{|(lartist, lfreq),(rartist,rfreq)| lfreq <=> rfreq}.reverse.first

        #names = eqls.map{|elm| elm[:name]}.permutation(2)
        #  .map{|name1, name2| 
        #    if name1.size > name2.size && name1.include?(name2) then
        #      name2
        #    else
        #      name1
        #    end
        #  }.uniq

        #names = eqls.map{|elm| elm[:name]} if names.empty?

        [artist, eqls.map{|elm|
          if hash_mode then
            elm[:name]
          else
            elm
          end
        }]
      }]
  end

  def to_csv(grouped_songs)
    sorted_keys = grouped_songs.keys.sort
    sorted_keys.map{|artist|
      sorted_names = grouped_songs[artist].sort
      sorted_names.each_with_index.map{|name, idx|
        if idx.zero? then
          [artist, name].flatten.to_csv
        else
          [nil, name].flatten.to_csv
        end
      }
    }.flatten.join
  end

  def update_csv(path)
    csv = CSV.read(path)
    yaml = csv.inject({}){|yaml, line|
      artist, name = line[0], line[1..]
      key = yaml[:key]
      
      if not artist.nil? and key != artist then
        key = yaml[:key] = artist
        yaml[key] = [name]
      else
        yaml[key] << name
      end

      yaml
    }.select{|k,v| k!=:key
    }.map{|artist, names| [artist, names.select{|name, flag| flag != ?x}]}

    return Hash[yaml]
  end

end
