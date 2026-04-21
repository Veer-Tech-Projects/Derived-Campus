export type CropAreaPixels = {
  x: number;
  y: number;
  width: number;
  height: number;
};

async function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Failed to load image for cropping."));
    image.src = src;
  });
}

export async function createCroppedImageFile(
  imageSrc: string,
  cropPixels: CropAreaPixels,
): Promise<File> {
  const image = await loadImage(imageSrc);

  const canvas = document.createElement("canvas");
  canvas.width = cropPixels.width;
  canvas.height = cropPixels.height;

  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Crop canvas context is not available.");
  }

  context.drawImage(
    image,
    cropPixels.x,
    cropPixels.y,
    cropPixels.width,
    cropPixels.height,
    0,
    0,
    cropPixels.width,
    cropPixels.height,
  );

  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (result) => {
        if (!result) {
          reject(new Error("Failed to generate cropped image."));
          return;
        }
        resolve(result);
      },
      "image/webp",
      0.92,
    );
  });

  return new File([blob], "avatar.webp", { type: "image/webp" });
}