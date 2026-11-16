(async () => {
  const images = {};
  for (const name of ['direct', 'approved', 'path', 'other', 'encoded']) {
    images[name] = await new Promise((resolve) => {
      const image = new Image();
      const deadline = setTimeout(() => resolve('timeout'), 5000);
      image.onload = () => {
        clearTimeout(deadline);
        resolve('loaded');
      };
      image.onerror = () => {
        clearTimeout(deadline);
        resolve('blocked');
      };
      image.src = `/image/${name}`;
    });
  }
  window.c09Images = {
    origin: `${location.protocol}//${location.host}`,
    cookie: document.cookie,
    serviceWorker: !!navigator.serviceWorker,
    images,
  };
})();
