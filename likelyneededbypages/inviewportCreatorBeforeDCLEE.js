function sleep(milliseconds){
    var start = new Date().getTime();
    var keep_looping = true;
    while (keep_looping) {
      if ((new Date().getTime() - start)> milliseconds) {
        keep_looping = false;
      }
    }
  }
(function() {
    'use strict';
    var imageNode = document.createElement('img');
    imageNode.src = 'sparrow.png?inviewport-jsloaded';
    var inviewportDiv = document.getElementById('inviewport-images');
    inviewportDiv.appendChild(imageNode);
    sleep(1500);
    var scriptLoader = document.createElement('script');
    scriptLoader.type = 'application/javascript';
    scriptLoader.src = 'inviewportCreatorAfterDCLEE.js';
    document.body.appendChild(scriptLoader);
})();
