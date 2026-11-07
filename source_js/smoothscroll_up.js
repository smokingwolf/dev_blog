/* Smooth scrolling
   Changes links that link to other parts of this page to scroll
   smoothly to those links rather than jump to them directly, which
   can be a little disorienting.
   
   sil, http://www.kryogenix.org/
   
   v1.0 2003-11-11
   v1.1 2005-06-16 wrap it up in an object
   
   [SmokingWOLFメモ]
   </HEAD>の前に
   <script src="smoothscroll.js" type="text/javascript"></script>  を入れる
   BODY内に<a id="link1"></a>　　を入れ、　<a href="#link1">AAA</a>　で飛べばOK。
   このトップのは a の指定が『id』であることに注意する。
   
   [改造地点]
    スクロール位置を少しマイナスしている。
*/

var ss = {
  fixAllLinks: function() {
    // Get a list of all links in the page
    var allLinks = document.getElementsByTagName('a');
    // Walk through the list
    for (var i=0;i<allLinks.length;i++) {
      var lnk = allLinks[i];
      if ((lnk.href && lnk.href.indexOf('#') != -1) && 
          ( (lnk.pathname == location.pathname) ||
	    ('/'+lnk.pathname == location.pathname) ) && 
          (lnk.search == location.search)) {
        ss.addEvent(lnk,'click',ss.smoothScroll);
      }
    }
  },

  // Open only the addendum that contains the requested anchor.
  revealHiddenAddenda: function(target) {
    var opened = false;
    for (var node = target; node && node !== document; node = node.parentNode) {
      if (node.classList && node.classList.contains('extended') &&
          window.getComputedStyle(node).display === 'none') {
        node.style.display = 'block';
        opened = true;
      }
    }
    return opened;
  },
  // A direct #link may be resolved before its hidden addendum is visible.
  followHashIntoAddendum: function() {
    var hash = window.location.hash;
    if (!hash || hash.length < 2) return;
    var anchor;
    try { anchor = decodeURIComponent(hash.slice(1)); }
    catch (e) { anchor = hash.slice(1); }
    var destination = document.getElementById(anchor);
    if (!destination || !ss.revealHiddenAddenda(destination)) return;

    setTimeout(function() {
      var y = destination.getBoundingClientRect().top + ss.getCurrentYPos() - 60;
      window.scrollTo(0, Math.max(0, y));
    }, 0);
  },

  smoothScroll: function(e) {
    if (window.event) {
      target = window.event.srcElement;
    } else if (e) {
      target = e.target;
    } else return;

    if (target.nodeName.toLowerCase() != 'a') {
      target = target.parentNode;
    }
  
    if (target.nodeName.toLowerCase() != 'a') return;
  
    // Find the <a name> tag corresponding to this href
    anchor = target.hash.substr(1);
    var allLinks = document.getElementsByTagName('a');
    var destinationLink = null;
    for (var i=0;i<allLinks.length;i++) {
      var lnk = allLinks[i];
      if (lnk.id && (lnk.id == anchor)) {
        destinationLink = lnk;
        break;
      }
    }
  
    if (!destinationLink) return true;

    ss.revealHiddenAddenda(destinationLink);
  
    // Find the destination's position
    var destx = destinationLink.offsetLeft;
    var desty = destinationLink.offsetTop;
    var thisNode = destinationLink;
    while (thisNode.offsetParent && 
          (thisNode.offsetParent != document.body)) {
      thisNode = thisNode.offsetParent;
      destx += thisNode.offsetLeft;
      desty += thisNode.offsetTop;
    }
    desty -= 60; // ←ここで60px上にスクロール位置を調整 //SmokingWOLF
  
    clearInterval(ss.INTERVAL);
  
    cypos = ss.getCurrentYPos();
  
    ss_stepsize = parseInt((desty-cypos)/ss.STEPS);
    ss.INTERVAL = setInterval('ss.scrollWindow('+ss_stepsize+','+desty+',"'+anchor+'")',10);
  
    if (window.event) {
      window.event.cancelBubble = true;
      window.event.returnValue = false;
    }
    if (e && e.preventDefault && e.stopPropagation) {
      e.preventDefault();
      e.stopPropagation();
    }
  },

  scrollWindow: function(scramount,dest,anchor) {
    wascypos = ss.getCurrentYPos();
    isAbove = (wascypos < dest);
    tmp = ( dest - wascypos ) / ss.STEPS;
    window.scrollTo(0,wascypos + tmp);
    iscypos = ss.getCurrentYPos();
    isAboveNow = (iscypos < dest);
    if ((isAbove != isAboveNow) || (wascypos == iscypos)) {
// window.scrollTo(0,dest);
      // cancel the repeating timer
      clearInterval(ss.INTERVAL);
// and jump to the link directly so the URL's right
//      location.hash = anchor;
    }
  },

  getCurrentYPos: function() {
    if (document.body && document.body.scrollTop)
      return document.body.scrollTop;
    if (document.documentElement && document.documentElement.scrollTop)
      return document.documentElement.scrollTop;
    if (window.pageYOffset)
      return window.pageYOffset;
    return 0;
  },

  addEvent: function(elm, evType, fn, useCapture) {
    if (elm.addEventListener){
      elm.addEventListener(evType, fn, useCapture);
      return true;
    } else if (elm.attachEvent){
      var r = elm.attachEvent("on"+evType, fn);
      return r;
    } else {
      alert("Handler could not be removed");
    }
  } 
}

ss.STEPS = 5;

ss.addEvent(window,"load",ss.fixAllLinks);
ss.addEvent(window,"load",ss.followHashIntoAddendum);
ss.addEvent(window,"hashchange",ss.followHashIntoAddendum);
