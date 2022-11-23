let fc = getCookie('friendCode');
let theMan = document.getElementById('secrety');
theMan.innerHTML = theMan.innerHTML.replace('XXXX-XXXX-XXXX', fc.match(/.{1,4}/g).join('-'));
