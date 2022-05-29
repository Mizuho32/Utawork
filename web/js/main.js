// 2. This code loads the IFrame Player API code asynchronously.
var tag = document.createElement('script');
tag.src = "https://www.youtube.com/iframe_api";

var firstScriptTag = document.getElementsByTagName('script')[0];
firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

// 3. This function creates an <iframe> (and YouTube player)
//    after the API code downloads.
var player;
function onYouTubeIframeAPIReady() {
  //player = load_video('M7lc1UVf-VE');

  //player = new YT.Player('player', {
  //  /*height: '360',
  //  width: '640',*/
  //  videoId: 'M7lc1UVf-VE',
  //  /*videoId: '4PEcgxNG27A',*/
  //  events: {
  //    'onReady': onPlayerReady,
  //    'onStateChange': onPlayerStateChange
  //  }
  //});
}

function stopVideo() {
  player.stopVideo();
}

function playVideo() {
  player.playVideo();
}


let table = document.querySelector("#stamps");
for (let i = 0; i < 10; i++) {
  insert_row(table, i, 20, 200);
}

/*$(function(){
	$.ajax({
		url: 'https://www.google.com/search?q=jquery',    // 表示させたいコンテンツがあるページURL
		cache: false,
		datatype: 'html',
		success: function(html) {
				var h = $(html).find('#rso');    // 表示させたいコンテンツの要素を指定
				$('#search').append(h);    // append関数で指定先の要素へ出力
				//document.querySelector("#search")
		}
	});
});*/

for (var i = 0, row; row = table.rows[i]; i++) {
  //console.log(row);
	//row.querySelector("td.start").addEventListener('change', timechange);
  apply_tablerow_shortcuts(row);
}
