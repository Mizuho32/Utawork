require 'open-uri'

require 'oga'
# https://qiita.com/TeQuiLayy/items/a74f928426dcb013e1cd
def google(word)
  user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.81 Safari/537.36"

  search_url = "https://www.google.co.jp/search?hl=jp&gl=JP&"
  query = URI.encode_www_form(q: word)
  search_url += query

  charset = nil

  html = URI.open(search_url, 'User-Agent' => user_agent) { |f|
      charset = f.charset
      f.read
  }

  #parsed = Oga.parse_html(
  #  html.encode("UTF-16BE", "UTF-8", :invalid => :replace, :undef => :replace, :replace => '?')
  #      .encode("UTF-8"))
  #return parsed.xpath("//div[@id='main']").first.to_xml
  return html

end

File.write(ARGV.first, google(ARGV[1]));
