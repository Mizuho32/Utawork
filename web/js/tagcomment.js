function copypaste() {
  /* Get the text field */
  let copyText = document.querySelector("code");

  /* Copy the text inside the text field */
  navigator.clipboard.writeText(copyText.innerText);

  /* Alert the copied text */
  //alert("Copied the text: " + copyText.innerText);

  let url = new URL(location.href);
  let video_id = url.searchParams.get("video_id");
  let yt = `https://youtube.com/watch?v=${video_id}`;
  window.open(yt, '_blank').focus();
  //window.location.assign(yt); // for mobile?
}
