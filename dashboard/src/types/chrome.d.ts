// Chrome Extension API 类型声明
// 这是一个全局声明文件，不应有 export {}

declare namespace chrome {
  namespace runtime {
    function sendMessage(
      extensionId: string,
      message: any,
      options?: any,
      callback?: (response: any) => void
    ): void;
    const onMessage: any;
    const id: string;
  }
}

interface Window {
  chrome: typeof chrome;
}