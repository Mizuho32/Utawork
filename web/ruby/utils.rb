require 'pathname'
require 'csv'
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

  def save_tags(vid, tags)
    id = video_id(vid)
    dir = DATA_DIR / id

    dir.mkdir if not dir.exist?

    csv = tags.map(&:to_csv).join
    ext = TAGS_FILE.extname
    File.write(dir/TAGS_FILE, csv)
    File.write(dir/"#{TAGS_FILE.basename(ext)}_#{DateTime.now.iso8601}#{ext}", csv)
  end

end
