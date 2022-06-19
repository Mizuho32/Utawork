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


var url;
let lock, locked;
window.onload = ()=>{
  url = new URL(location.href);

  // get lock
  let video_id = url.searchParams.get("video_id");
  if (video_id && url.searchParams.get("lock")) {
    setTimeout(function (){
      [lock, locked] = get_lock(url)

      if (!locked) {
        url.searchParams.set("lock", lock);
        window.history.pushState(null, document.title, url.search);

        ws_ensure(
          (socket, e)=>socket.send(JSON.stringify({lock: lock, video_id: video_id})),
          (e)=>{
            if (e.data != lock) {
              alert("ロック取得失敗。他の人が作業中の可能性があります");
              lock = "";
            }
          },
          ()=> {
            alert("ロック取得がタイムアウト。他の人が作業中の可能性があります");
            lock = "";
          },
          1000);
      }
    }, 1000);
  }

  if (url.searchParams.get("nonPC")) {
    mobile = true;
  }

  if (!url.searchParams.get("notgl") && is_mobile_html()) {
    toggle_info(true); // open
  }

  let times = document.querySelector("#raw_times_input").textContent;
  if (times) {
    load_segments(times);
    document.querySelector("#segments").checked = true;
  } else {
    if (url.searchParams.get("d")) {
      let table = document.querySelector("#stamps");
      let len = 10;
      for (let i = 0; i < len; i++) {
        let s = (len-i)*10;
        insert_row(table, i, s, s+180);
      }
    }
  }

  //if (/^((?!chrome|android).)*safari/i.test(navigator.userAgent)) { // Safari. 🖕 🍎
  //  window.onpagehide = onclose;
  //}
  //window.addEventListener('beforeunload', (event) => {
  //  //Cancel the event as stated by the standard.
  //  event.preventDefault();
  //  // Chrome requires returnValue to be set.
  //  event.returnValue = 'Hello2';

  //  onclose();
  //  return "HI";
  //});
};


window.onbeforeunload = function (e) {
  e = e || window.event;

  if (lock) {
    onclose();

    // For IE and Firefox prior to version 4
    if (e) {
        e.returnValue = '閉じます';
    }

    // For Safari
    return '閉じます';
  }
};

function onclose() {

  let video_id = url.searchParams.get("video_id");
  if (lock) {
    //let socket = new WebSocket(`ws://${location.host}/websocket`);
    //socket.send(JSON.stringify({unlock: lock, video_id: video_id}));

    ws_ensure(
      (socket, e)=>socket.send(JSON.stringify({unlock: lock, video_id: video_id})),
      (e)=>{
        if (e.data == lock) {
          lock = "";
          url.searchParams.set("lock", "none");
          window.history.pushState(null, document.title, url.search);
        } else {
          alert(`ロック解除失敗。報告してください。\n${video_id}`);
        }
      },
      ()=> {
          alert(`ロック解除タイムアウト。報告してください。\n${video_id}`);
      },
      1000);
  }

}
