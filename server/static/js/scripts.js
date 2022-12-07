/*!
    * Start Bootstrap - SB Admin v7.0.5 (https://startbootstrap.com/template/sb-admin)
    * Copyright 2013-2022 MCMi460
    * Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-sb-admin/blob/master/LICENSE)
    */
    //
// Scripts
//

function getCookie(cname) {
  let name = cname + "=";
  let ca = document.cookie.split(';');
  for(let i = 0; i < ca.length; i++) {
    let c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}

var accountList = document.getElementById('accountSymbol');
if (!getCookie('token') && accountList)
{
  var child = accountList.lastElementChild; 
  for (let i = 0; i < 3; i++)
  {
    accountList.removeChild(child);
    child = accountList.lastElementChild;
  }
  child.firstChild.href = '/login.html';
  child.firstChild.text = 'Login';
}

let fcItem = document.getElementById('botFC');
if (fcItem)
{
  fcItem.innerHTML = fcItem.innerHTML.replace('X', '2337-9054-8638'); // Put your own botFC here
}

/*
let fcItem2 = document.getElementById('userFC');
if (fcItem2)
{
  fcItem2.innerHTML = fcItem2.innerHTML.replace('X', getCookie('fc'));
}*/

window.addEventListener('DOMContentLoaded', event => {

    // Toggle the side navigation
    const sidebarToggle = document.body.querySelector('#sidebarToggle');
    if (sidebarToggle) {
        // Uncomment Below to persist sidebar toggle between refreshes
        // if (localStorage.getItem('sb|sidebar-toggle') === 'true') {
        //     document.body.classList.toggle('sb-sidenav-toggled');
        // }
        sidebarToggle.addEventListener('click', event => {
            event.preventDefault();
            document.body.classList.toggle('sb-sidenav-toggled');
            localStorage.setItem('sb|sidebar-toggle', document.body.classList.contains('sb-sidenav-toggled'));
        });
    }

});
