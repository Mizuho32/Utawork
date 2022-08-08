require 'pathname'
require 'csv'
require 'date'
require 'yaml'
require 'date'

module Utils
  extend self

  DATA_DIR = Pathname("data")
  SEGMENTS_FILE = Pathname("segments.tsv")
  TAGS_FILE = Pathname("tags.csv")

  def init()
    DATA_DIR.mkdir if not DATA_DIR.exist?
  end

  # https://qiita.com/TeQuiLayy/items/a74f928426dcb013e1cd
  def google(word)
    #user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36"
    user_agent = "(｀・ω・´)" # not to load images(?)

    search_url = "https://www.google.co.jp/search?hl=jp&gl=JP&"
    query = URI.encode_www_form(q: word)
    search_url += query

    charset = nil

    html = URI.open(search_url, 'User-Agent' => user_agent) { |f|
        charset = f.charset
        f.read
    }

    parsed = Oga.parse_html(
      html.encode("UTF-16BE", "UTF-8", :invalid => :replace, :undef => :replace, :replace => '?')
          .encode("UTF-8"))
    return parsed.xpath("//div[@id='main']").first.to_xml

  end

  def video_id(url)
    if url.include?("youtu") then
      return url[/(?:v=|\.be\/)([^=&\/]+)/i, 1]
    end

    return url # looks id
  end

  def load_segments(vid)
    id = video_id(vid)
    text = if not id.empty? and (file = DATA_DIR / id / SEGMENTS_FILE).exist? then
             File.read(file)
           else
             ""
           end
    return id, text
  end

  def load_tags(vid)
    dir = ensure_dir(vid)
    return CSV.read(dir/TAGS_FILE)
  end

  def ensure_dir(vid)
    id = video_id(vid)
    dir = DATA_DIR / id

    dir.mkdir if not dir.exist?
    dir
  end

  def save_tags(vid, tags)
    dir = ensure_dir(vid)

    csv = tags.map(&:to_csv).join
    ext = TAGS_FILE.extname
    File.write(dir/TAGS_FILE, csv)
    File.write(dir/"#{TAGS_FILE.basename(ext)}_#{DateTime.now.iso8601}#{ext}", csv)
  end

  def save_segments(vid, tsv)
    dir = ensure_dir(vid)

    ext = SEGMENTS_FILE.extname
    File.write(dir/SEGMENTS_FILE, tsv)
    File.write(dir/"#{SEGMENTS_FILE.basename(ext)}_#{DateTime.now.iso8601}#{ext}", tsv)
  end

  def remove_bundler(ex)
    ex.backtrace.select{|line| not line.include?("bundle")}
  end

  def load_list(path)
    list = YAML.unsafe_load_file(path).inject({}){|hash, el|
      hash[el[:video_id].to_sym] = el
      hash
    }

    return renew_list(list)
  end

  def renew_list(list)
    DATA_DIR.glob("*/").each{|dir|
      id = dir.basename.to_s.to_sym
      id_exists = list.has_key?(id)
      list[id][:has_segments] = true if id_exists and (dir / SEGMENTS_FILE).exist?
      list[id][:has_tags]     = true if id_exists and (dir / TAGS_FILE).exist?
    }
    list
  end

  def save_list(path, list)
    File.write(path, list.values.to_yaml)
  end

  def decode_videoinfo(item)
    item2 = {**item}
    item2[:duration]     = in_seconds(item2[:duration])
    item2[:published_at] = item2[:published_at].iso8601
    return item2
  end

  # https://gist.github.com/natritmeyer/b04e219f63644948d9be
  def in_seconds(raw_duration)
    match = raw_duration.match(/PT(?:([0-9]*)H)*(?:([0-9]*)M)*(?:([0-9.]*)S)*/)
    hours   = match[1].to_i
    minutes = match[2].to_i
    seconds = match[3].to_f
    seconds + (60 * minutes) + (60 * 60 * hours)
  end
end

