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
}

function onPlayerStateChange(e) {
  let btn = document.querySelector("#yt_playpause");
  if (e.data == YT.PlayerState.PLAYING || e.data == YT.PlayerState.BUFFERING) { // start
    btn.setAttribute("class", btn.getAttribute("class").replace("play", "pause"));
  } else { // pause
    btn.setAttribute("class", btn.getAttribute("class").replace("pause", "play"));
  }
}

function stopVideo() {
  if (player) player.stopVideo();
}

function playVideo() {
  if (player) player.playVideo();
}


window.onload = ()=>{
  if (location.search.match(/(?:\?|&)nonPC=/)) {
    mobile = true;
  }

  if (!location.search.match(/(?:\?|&)notgl=/) && is_mobile_html()) {
    toggle_info(true); // open
  }

  let times = document.querySelector("#raw_times_input").textContent;
  if (times) {
    load_segments(times);
    document.querySelector("#segments").checked = true;
  } else {
    if (location.search.match(/(?:\?|&)d=/)) {
      let table = document.querySelector("#stamps");
      let len = 10;
      for (let i = 0; i < len; i++) {
        let s = (len-i)*10;
        insert_row(table, i, s, s+180);
      }
    }
  }
};
