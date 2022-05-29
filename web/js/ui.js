function timeinput_nonPC(time, is_start) {
  let startend = is_start ? "start" : "end";
  let time_input = `
  <div class="time_input">
    <input type="text" class="time ${startend}" value="${time}" onchange="timechange(event);" readonly="readonly" ontouchend="touchend(event);"/>
    <div class="time_buttons">
      <button class="fa-solid fa-minus" onclick="changetime(event, -1)"></button>
      <button class="fa-solid fa-plus"  onclick="changetime(event, +1)"></button>
    </div>
  </div>
`;
  if (is_start) {
    return `
    ${time_input}
    <button class="fa-solid fa-backward-step" ontouchend="seek_to(event);"></button>`;
  } else {
    return `
    <button class="fa-solid fa-forward-step"  ontouchend="seek_to(event);"></button>
    ${time_input}
    `;
  }
}

function gen_timeinput(value, is_start=true) {
  let startend = is_start ? "start" : "end";
  if (detectMobile()) {
    let div = `<div class="time ${startend}">`;
    return `${div}${timeinput_nonPC(value, is_start)}</div>`;
  } else {
    return `<input type="time" class="time ${startend}" value="${value}" onchange="timechange(event);" />`;
  }
}

function segment_row(idx, start, end) {
  let no_col = `
<td class="no">
  <div>
  <label style="text-align: center;" >${idx}</label>
  <input type="checkbox"></input>
  <i class="fa-solid fa-trash" style="text-align: center;" ></i>
  </div>
</td>`;

  if (is_mobile_html()) {
    return `
${no_col}
<td class="item">
<table>
  <tr>
    <td><label class="start">Start time</label></td>
    <td><label class="ldngth">Length</label></td>
    <td><label class="end">End time</label></td>
  </tr>
  <tr>
    <td>${ gen_timeinput(to_time(start)) }</td>
    <td><div class="length">${to_time(end-start, 2)}</div></td>
    <td>${ gen_timeinput(to_time(end), false) }</td>
  </tr>
</table>
  <div class="name">
    <button class="fa-solid fa-magnifying-glass" onclick="search_button(event)"></button>
    <input type="text" class="name" onfocus="on_songname_focus(event);" placeholder="Song name"></input>
  </div>
  <div class="artist"><input type="text" class="artist" placeholder="Artist"></input></div>
</td>`;
  } else {
    return `
${no_col}
<td class="time start">${ gen_timeinput(to_time(start)) }</td>
<td class="time end">${   gen_timeinput(to_time(end), false) }</td>
<td class="length">${to_time(end-start, 2)}</td>
<td class="name">
  <button class="fa-solid fa-magnifying-glass" onclick="search_button(event)"></button>
  <input type="text" class="name" onfocus="on_songname_focus(event);"></input>
</td>
<td class="artist"><input type="text" class="artist"></input></td>`;
  }
}

function insert_row(table, idx, start, end) {
  if (idx < 0) idx = table.rows.length;

  let new_row = table.insertRow(-1);
  new_row.setAttribute("class", "item");
  new_row.innerHTML = segment_row(idx, start, end);
  if (!is_mobile_html()) apply_tablerow_shortcuts(new_row);
  return new_row;
}
