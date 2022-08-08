require 'pathname'
require 'csv'
require 'date'
require 'yaml'
require 'date'

module ExportUtils
  extend self

  FULL_DATE_EXP = %r|(?<y>\d+)/(?<m>\d+)/(?<d>\d+)|
  SIMPLE_DATE_EXP = %r|(?<y>\d{2})(?<m>\d{2})(?<d>\d{2})|
  JP_DATE_EXP = %r|R(?<y>\d)(?<m>\d{2})(?<d>\d{2})|
  DATE_EXP = %r/(?<full>#{FULL_DATE_EXP})|(?<simple>#{SIMPLE_DATE_EXP})|(?<jp>#{JP_DATE_EXP})/

  def estimate_pubdate(item)
    title_date_match = item[:title].match(DATE_EXP)

    if m = title_date_match then
      estim = to_datetime(m[:y].to_i, m[:m].to_i, m[:d].to_i, m.named_captures["jp"])
      if estim - item[:published_at] < -365 then # estim is over 1year past than published
        return item[:published_at]
      else
        return estim
      end
    else
      return item[:published_at]
    end
  end

  def to_datetime(y,m,d, is_jp)

    y += 2018 if is_jp
    y += 2000 if y < 2000

    return DateTime.new(y,m,d,0,0,0, "+9:00")
  end

end

