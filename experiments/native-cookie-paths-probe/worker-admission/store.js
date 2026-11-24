window.workerAdmissionData = async (value) => {
  const name = 'worker-admission-fixture';
  const reading = value === undefined;
  if (reading && !(await indexedDB.databases()).some((database) => database.name === name)) {
    return null;
  }
  const database = await new Promise((resolve, reject) => {
    const open = indexedDB.open(name, 1);
    open.onupgradeneeded = () => {
      if (reading) {
        open.transaction.abort();
      } else {
        open.result.createObjectStore('markers');
      }
    };
    open.onsuccess = () => resolve(open.result);
    open.onerror = () => reject(open.error);
  });
  try {
    return await new Promise((resolve, reject) => {
      const transaction = database.transaction('markers', reading ? 'readonly' : 'readwrite');
      const store = transaction.objectStore('markers');
      const request = reading ? store.get('run') : store.put(value, 'run');
      transaction.oncomplete = () => resolve(reading ? (request.result ?? null) : value);
      transaction.onabort = () => reject(transaction.error);
    });
  } finally {
    database.close();
  }
};
