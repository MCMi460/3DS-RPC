//
// Scripts
//

console.log('%cIf you\'re looking at this text, I think you\'re pretty cool!', 'color: #42f578');

function getCookie(cname) {
  let name = cname + '=';
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
  return '';
}
function eraseCookie(name) {
    document.cookie = name +'=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
}
function deleteFriendcode() {
    eraseCookie('FC');
    eraseCookie('MII');
    location.reload();
}

var account = document.getElementById('accountDropdown')
var nav = document.getElementById('navbarDropdown')
const FC = getCookie('FC');
const MII = getCookie('MII');
console.log(`User's FC: ${FC}`);
console.log(`User's Mii: ${MII}`);
if (account) {
  var accountList = account.getElementsByTagName('li');
  if (FC == '')
  {
    account.removeChild(accountList[0]);
    account.removeChild(accountList[0]);
  } else {
    account.removeChild(accountList[2]);
    accountList[0].firstChild.href = '/user/' + FC;
  }
}
if (MII != '' && nav) {
  nav.innerHTML = `<img height = '50px' src = '${MII}' />`;
}

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
            if (settings) {
                window.location.href = '/';
            }
        });
    }

});
