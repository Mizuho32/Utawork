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

function stopVideo() {
  player.stopVideo();
}

function playVideo() {
  player.playVideo();
}


window.onload = ()=>{
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
