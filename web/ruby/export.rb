require 'pathname'
require 'csv'
require 'date'
require 'yaml'
require 'date'

require_relative 'export_utils'

# ARGV
# 0: data/ path
# - data/list.yaml
# - data/video_id/tags.csv
# - ....
# 1: sort by title y/n
# 2: target dir

sort_by_title = ARGV[1].include?("y")
target_dir = Pathname(ARGV[2])
data_dir = Pathname(ARGV.first)

list = YAML.unsafe_load_file(data_dir / "list.yaml")
  .map{|item|
    item[:estimated_date] = ExportUtils.estimate_pubdate(item)
    item
  }
  .sort{|l,r|
    l[:estimated_date] <=> r[:estimated_date]
  }.map{|item|
    [item[:title], item[:video_id], "unlisted", item[:estimated_date].iso8601]
  }.reverse

# write uploads.csv
csv = list.map(&:to_csv).join
File.write(target_dir / "uploads.csv", csv)

# video info yaml generation
utawaku_dir = target_dir / "singing_streams"
Dir.mkdir(utawaku_dir) if !utawaku_dir.exist?

list.each{|item|
  title, video_id, _, up_date = item
  tags_path = data_dir / video_id / "tags.csv"

  next if !tags_path.exist?

  item = {
    title: title,
    id: video_id,
    published_at: up_date,
    setlist: CSV.read(tags_path) # start end title artist
      .select{|line| !line[2].empty? && !line[3].empty? }
      .map{|line|
        { time: line[0], body: {song_name: line[2], artist: line[3]}, lines:[] }
      }
  }

  if item[:setlist].empty? then
    puts "#{title} is empty..."
    next
  end

  File.write(utawaku_dir / "#{item[:id]}.yaml", item.to_yaml)
}

# Sample
=begin

:title: "【 2022年歌枠初め 】好きな歌をうたうよ！～Singing stream～【 #なまのとと 】"
:id: 0nnixihUxE0
:splitters:
- "/"
- "|"
- "("
- ")"
:setlist:
- :time: '00:12:08'
  :lines:
  - 本能 / Honnoh | 椎名林檎 (Sheena Ringo)
  :splitted:
  - 本能
  - Honnoh
  - 椎名林檎
  - Sheena Ringo
  :body:
    :song_name: 本能
    :artist: 椎名林檎
    :song_name_en: Honnoh
    :artist_en: Sheena Ringo
- :time: '00:18:35'



00:01:56,00:05:50,弱虫モンブラン,DECO*27
00:11:09,00:13:25,KING,Kanaria
00:14:31,00:19:05,初音ミクの消失,cosMo@暴走P
00:21:00,00:24:26,踊,Ado
00:26:23,00:30:15,千本桜,黒うさP
00:32:05,00:36:45,ブラック★ロックシューター,ryo
00:38:16,00:41:25,人生は夢だらけ,椎名林檎
00:42:40,00:45:02,Almost There ,Randy Newman
00:53:14,00:56:15,ドレミファロンド,40メートルP

- :title: 220310昼 ※戴き物　歌枠
  :video_id: 4PEcgxNG27A
  :published_at: !ruby/object:DateTime 2022-05-17 21:58:50.000000000 +09:00
  :duration: PT59M23S
=end
