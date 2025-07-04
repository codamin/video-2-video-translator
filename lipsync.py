import argparse
import os
import numpy as np
import cv2
import torch
import glob
import pickle
import sys
from tqdm import tqdm
import copy
import json
from transformers import WhisperModel

from musetalk.utils.face_parsing import FaceParsing
from musetalk.utils.utils import datagen
from musetalk.utils.preprocessing import get_landmark_and_bbox, read_imgs
from musetalk.utils.blending import get_image_prepare_material, get_image_blending
from musetalk.utils.utils import load_all_model
from musetalk.utils.audio_processor import AudioProcessor

import shutil
import threading
import queue
import time
import subprocess
from types import SimpleNamespace

defaults = {
    "ffmpeg_path": "/usr/local/lib/python3.10/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2",
    "gpu_id": 0,
    "unet_model_path": "./models/musetalk/pytorch_model.bin",
    "vae_type": "sd-vae",
    "unet_config": "./models/musetalk/musetalk.json",
    "whisper_dir": "./models/whisper",
    "version": "v15",
    "left_cheek_width": 90,
    "right_cheek_width": 90,
    "batch_size": 20,
    "fps": 25,
    "skip_save_images": True,
    "inference_config": "configs/inference/realtime.yaml"
}
default_cfg = SimpleNamespace(**defaults)


def fast_check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except:
        return False

def video2imgs(vid_path, save_path, ext='.png', cut_frame=10000000):
    cap = cv2.VideoCapture(vid_path)
    count = 0
    while True:
        if count > cut_frame:
            break
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"{save_path}/{count:08d}.png", frame)
            count += 1
        else:
            break


def osmakedirs(path_list):
    for path in path_list:
        os.makedirs(path) if not os.path.exists(path) else None

@torch.no_grad()
class Avatar:
    def __init__(self, avatar_id, video_path, bbox_shift, batch_size, preparation, unet, vae, audio_processor, whisper, pe, fp, args=default_cfg):
        self.avatar_id = avatar_id
        self.video_path = video_path
        self.bbox_shift = bbox_shift
        # 根据版本设置不同的基础路径
        if args.version == "v15":
            self.base_path = f"./results/{args.version}/avatars/{avatar_id}"
        else:  # v1
            self.base_path = f"./results/avatars/{avatar_id}"
            
        self.avatar_path = self.base_path
        self.full_imgs_path = f"{self.avatar_path}/full_imgs"
        self.coords_path = f"{self.avatar_path}/coords.pkl"
        self.latents_out_path = f"{self.avatar_path}/latents.pt"
        self.video_out_path = f"{self.avatar_path}/vid_output/"
        self.mask_out_path = f"{self.avatar_path}/mask"
        self.mask_coords_path = f"{self.avatar_path}/mask_coords.pkl"
        self.avatar_info_path = f"{self.avatar_path}/avator_info.json"
        self.avatar_info = {
            "avatar_id": avatar_id,
            "video_path": video_path,
            "bbox_shift": bbox_shift,
            "version": args.version
        }
        self.preparation = preparation
        self.batch_size = batch_size
        self.idx = 0

        self.args = args
        self.unet = unet
        self.vae = vae
        self.audio_processor = audio_processor
        self.weight_dtype = unet.model.dtype
        self.device = torch.device(f"cuda:{args.gpu_id}" if torch.cuda.is_available() else "cpu")
        self.timesteps = torch.tensor([0], device=self.device)
        self.whisper = whisper
        self.pe = pe
        self.fp = fp

        self.init()

    def init(self):
        if self.preparation:
            if os.path.exists(self.avatar_path):
                response = input(f"{self.avatar_id} exists, Do you want to re-create it ? (y/n)")
                if response.lower() == "y":
                    shutil.rmtree(self.avatar_path)
                    print("*********************************")
                    print(f"  creating avator: {self.avatar_id}")
                    print("*********************************")
                    osmakedirs([self.avatar_path, self.full_imgs_path, self.video_out_path, self.mask_out_path])
                    self.prepare_material()
                else:
                    self.input_latent_list_cycle = torch.load(self.latents_out_path)
                    with open(self.coords_path, 'rb') as f:
                        self.coord_list_cycle = pickle.load(f)
                    input_img_list = glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
                    input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                    self.frame_list_cycle = read_imgs(input_img_list)
                    with open(self.mask_coords_path, 'rb') as f:
                        self.mask_coords_list_cycle = pickle.load(f)
                    input_mask_list = glob.glob(os.path.join(self.mask_out_path, '*.[jpJP][pnPN]*[gG]'))
                    input_mask_list = sorted(input_mask_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                    self.mask_list_cycle = read_imgs(input_mask_list)
            else:
                print("*********************************")
                print(f"  creating avator: {self.avatar_id}")
                print("*********************************")
                osmakedirs([self.avatar_path, self.full_imgs_path, self.video_out_path, self.mask_out_path])
                self.prepare_material()
        else:
            if not os.path.exists(self.avatar_path):
                print(f"{self.avatar_id} does not exist, you should set preparation to True")
                sys.exit()

            with open(self.avatar_info_path, "r") as f:
                avatar_info = json.load(f)

            if avatar_info['bbox_shift'] != self.avatar_info['bbox_shift']:
                response = input(f" 【bbox_shift】 is changed, you need to re-create it ! (c/continue)")
                if response.lower() == "c":
                    shutil.rmtree(self.avatar_path)
                    print("*********************************")
                    print(f"  creating avator: {self.avatar_id}")
                    print("*********************************")
                    osmakedirs([self.avatar_path, self.full_imgs_path, self.video_out_path, self.mask_out_path])
                    self.prepare_material()
                else:
                    sys.exit()
            else:
                self.input_latent_list_cycle = torch.load(self.latents_out_path)
                with open(self.coords_path, 'rb') as f:
                    self.coord_list_cycle = pickle.load(f)
                input_img_list = glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]'))
                input_img_list = sorted(input_img_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                self.frame_list_cycle = read_imgs(input_img_list)
                with open(self.mask_coords_path, 'rb') as f:
                    self.mask_coords_list_cycle = pickle.load(f)
                input_mask_list = glob.glob(os.path.join(self.mask_out_path, '*.[jpJP][pnPN]*[gG]'))
                input_mask_list = sorted(input_mask_list, key=lambda x: int(os.path.splitext(os.path.basename(x))[0]))
                self.mask_list_cycle = read_imgs(input_mask_list)

    def prepare_material(self):
        print("preparing data materials ... ...")
        with open(self.avatar_info_path, "w") as f:
            json.dump(self.avatar_info, f)

        if os.path.isfile(self.video_path):
            video2imgs(self.video_path, self.full_imgs_path, ext='png')
        else:
            print(f"copy files in {self.video_path}")
            files = os.listdir(self.video_path)
            files.sort()
            files = [file for file in files if file.split(".")[-1] == "png"]
            for filename in files:
                shutil.copyfile(f"{self.video_path}/{filename}", f"{self.full_imgs_path}/{filename}")
        input_img_list = sorted(glob.glob(os.path.join(self.full_imgs_path, '*.[jpJP][pnPN]*[gG]')))

        print("extracting landmarks...")
        coord_list, frame_list = get_landmark_and_bbox(input_img_list, self.bbox_shift)
        input_latent_list = []
        idx = -1
        # maker if the bbox is not sufficient
        coord_placeholder = (0.0, 0.0, 0.0, 0.0)
        for bbox, frame in zip(coord_list, frame_list):
            idx = idx + 1
            if bbox == coord_placeholder:
                continue
            x1, y1, x2, y2 = bbox
            if self.args.version == "v15":
                y2 = y2 + self.args.extra_margin
                y2 = min(y2, frame.shape[0])
                coord_list[idx] = [x1, y1, x2, y2]  # 更新coord_list中的bbox
            crop_frame = frame[y1:y2, x1:x2]
            resized_crop_frame = cv2.resize(crop_frame, (256, 256), interpolation=cv2.INTER_LANCZOS4)
            latents = self.vae.get_latents_for_unet(resized_crop_frame)
            input_latent_list.append(latents)

        self.frame_list_cycle = frame_list + frame_list[::-1]
        self.coord_list_cycle = coord_list + coord_list[::-1]
        self.input_latent_list_cycle = input_latent_list + input_latent_list[::-1]
        self.mask_coords_list_cycle = []
        self.mask_list_cycle = []

        for i, frame in enumerate(tqdm(self.frame_list_cycle)):
            cv2.imwrite(f"{self.full_imgs_path}/{str(i).zfill(8)}.png", frame)

            x1, y1, x2, y2 = self.coord_list_cycle[i]
            if self.args.version == "v15":
                mode = self.args.parsing_mode
            else:
                mode = "raw"
            mask, crop_box = get_image_prepare_material(frame, [x1, y1, x2, y2], fp=self.fp, mode=mode)

            cv2.imwrite(f"{self.mask_out_path}/{str(i).zfill(8)}.png", mask)
            self.mask_coords_list_cycle += [crop_box]
            self.mask_list_cycle.append(mask)

        with open(self.mask_coords_path, 'wb') as f:
            pickle.dump(self.mask_coords_list_cycle, f)

        with open(self.coords_path, 'wb') as f:
            pickle.dump(self.coord_list_cycle, f)

        torch.save(self.input_latent_list_cycle, os.path.join(self.latents_out_path))

    def process_frames(self, res_frame_queue, video_len, skip_save_images):
        print(video_len)
        while True:
            if self.idx >= video_len - 1:
                break
            try:
                start = time.time()
                res_frame = res_frame_queue.get(block=True, timeout=1)
            except queue.Empty:
                continue

            bbox = self.coord_list_cycle[self.idx % (len(self.coord_list_cycle))]
            ori_frame = copy.deepcopy(self.frame_list_cycle[self.idx % (len(self.frame_list_cycle))])
            x1, y1, x2, y2 = bbox
            try:
                res_frame = cv2.resize(res_frame.astype(np.uint8), (x2 - x1, y2 - y1))
            except:
                continue
            mask = self.mask_list_cycle[self.idx % (len(self.mask_list_cycle))]
            mask_crop_box = self.mask_coords_list_cycle[self.idx % (len(self.mask_coords_list_cycle))]
            combine_frame = get_image_blending(ori_frame,res_frame,bbox,mask,mask_crop_box)

            if skip_save_images is False:
                cv2.imwrite(f"{self.avatar_path}/tmp/{str(self.idx).zfill(8)}.png", combine_frame)
            self.idx = self.idx + 1

    def inference(self, audio_path, out_vid_name, fps, skip_save_images):
        os.makedirs(self.avatar_path + '/tmp', exist_ok=True)
        print("start inference")
        ############################################## extract audio feature ##############################################
        start_time = time.time()
        # Extract audio features
        whisper_input_features, librosa_length = self.audio_processor.get_audio_feature(audio_path, weight_dtype=self.weight_dtype)
        whisper_chunks = self.audio_processor.get_whisper_chunk(
            whisper_input_features,
            self.device,
            self.weight_dtype,
            self.whisper,
            librosa_length,
            fps=fps,
            audio_padding_length_left=self.args.audio_padding_length_left,
            audio_padding_length_right=self.args.audio_padding_length_right,
        )
        print(f"processing audio:{audio_path} costs {(time.time() - start_time) * 1000}ms")
        ############################################## inference batch by batch ##############################################
        video_num = len(whisper_chunks)
        res_frame_queue = queue.Queue()
        self.idx = 0
        # Create a sub-thread and start it
        process_thread = threading.Thread(target=self.process_frames, args=(res_frame_queue, video_num, skip_save_images))
        process_thread.start()

        gen = datagen(whisper_chunks,
                     self.input_latent_list_cycle,
                     self.batch_size)
        start_time = time.time()
        res_frame_list = []

        for i, (whisper_batch, latent_batch) in enumerate(tqdm(gen, total=int(np.ceil(float(video_num) / self.batch_size)))):
            audio_feature_batch = self.pe(whisper_batch.to(self.device))
            latent_batch = latent_batch.to(device=self.device, dtype=self.unet.model.dtype)

            pred_latents = self.unet.model(latent_batch,
                                    self.timesteps,
                                    encoder_hidden_states=audio_feature_batch).sample
            pred_latents = pred_latents.to(device=self.device, dtype=self.vae.vae.dtype)
            recon = self.vae.decode_latents(pred_latents)
            for res_frame in recon:
                res_frame_queue.put(res_frame)
        # Close the queue and sub-thread after all tasks are completed
        process_thread.join()

        if self.args.skip_save_images is True:
            print('Total process time of {} frames without saving images = {}s'.format(
                video_num,
                time.time() - start_time))
        else:
            print('Total process time of {} frames including saving images = {}s'.format(
                video_num,
                time.time() - start_time))

        if out_vid_name is not None and self.args.skip_save_images is False:
            # optional
            cmd_img2video = f"ffmpeg -y -v warning -r {fps} -f image2 -i {self.avatar_path}/tmp/%08d.png -vcodec libx264 -vf format=yuv420p -crf 18 {self.avatar_path}/temp.mp4"
            print(cmd_img2video)
            os.system(cmd_img2video)

            output_vid = os.path.join(self.video_out_path, out_vid_name + ".mp4")  # on
            cmd_combine_audio = f"ffmpeg -y -v warning -i {audio_path} -i {self.avatar_path}/temp.mp4 {output_vid}"
            print(cmd_combine_audio)
            os.system(cmd_combine_audio)

            os.remove(f"{self.avatar_path}/temp.mp4")
            shutil.rmtree(f"{self.avatar_path}/tmp")
            print(f"result is save to {output_vid}")
        print("\n")

def lipsync(
    video_path: str,
    audio_path: str,
    output_vid_name: str = "output",
    avatar_id: str = "avatar_001",
    version: str = "v15",
    ffmpeg_path: str = "./ffmpeg-4.4-amd64-static/",
    gpu_id: int = 0,
    vae_type: str = "sd-vae",
    unet_config: str = "./models/musetalk/musetalk.json",
    unet_model_path: str = "./models/musetalk/pytorch_model.bin",
    whisper_dir: str = "./models/whisper",
    inference_config: str = "configs/inference/realtime.yaml",
    bbox_shift: int = 0,
    result_dir: str = './results',
    extra_margin: int = 10,
    fps: int = 25,
    audio_padding_length_left: int = 2,
    audio_padding_length_right: int = 2,
    batch_size: int = 20,
    use_saved_coord: bool = False,
    saved_coord: bool = False,
    parsing_mode: str = "jaw",
    left_cheek_width: int = 90,
    right_cheek_width: int = 90,
    skip_save_images: bool = False,
    preparation: bool = True,
):
    
    # Local args container
    class Args:
        pass

    args = Args()
    args.version = version
    args.ffmpeg_path = ffmpeg_path
    args.gpu_id = gpu_id
    args.vae_type = vae_type
    args.unet_config = unet_config
    args.unet_model_path = unet_model_path
    args.whisper_dir = whisper_dir
    args.inference_config = inference_config
    args.bbox_shift = bbox_shift
    args.result_dir = result_dir
    args.extra_margin = extra_margin
    args.fps = fps
    args.audio_padding_length_left = audio_padding_length_left
    args.audio_padding_length_right = audio_padding_length_right
    args.batch_size = batch_size
    args.output_vid_name = output_vid_name
    args.use_saved_coord = use_saved_coord
    args.saved_coord = saved_coord
    args.parsing_mode = parsing_mode
    args.left_cheek_width = left_cheek_width
    args.right_cheek_width = right_cheek_width
    args.skip_save_images = skip_save_images

    # Make it global for inner class access
    globals()["args"] = args

    def fast_check_ffmpeg():
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except:
            return False

    # Ensure FFmpeg
    if not fast_check_ffmpeg():
        print("Adding ffmpeg to PATH")
        path_separator = ';' if sys.platform == 'win32' else ':'
        os.environ["PATH"] = f"{args.ffmpeg_path}{path_separator}{os.environ['PATH']}"
        if not fast_check_ffmpeg():
            print("Warning: Unable to find ffmpeg, please ensure ffmpeg is properly installed")

    # Load device
    device = torch.device(f"cuda:{args.gpu_id}" if torch.cuda.is_available() else "cpu")

    # Load models
    vae, unet, pe = load_all_model(
        unet_model_path=args.unet_model_path,
        vae_type=args.vae_type,
        unet_config=args.unet_config,
        device=device
    )
    timesteps = torch.tensor([0], device=device)

    pe = pe.half().to(device)
    vae.vae = vae.vae.half().to(device)
    unet.model = unet.model.half().to(device)

    # Load Whisper
    audio_processor = AudioProcessor(feature_extractor_path=args.whisper_dir)
    weight_dtype = unet.model.dtype
    whisper = WhisperModel.from_pretrained(args.whisper_dir)
    whisper = whisper.to(device=device, dtype=weight_dtype).eval()
    whisper.requires_grad_(False)

    # Face parser
    if args.version == "v15":
        fp = FaceParsing(
            left_cheek_width=args.left_cheek_width,
            right_cheek_width=args.right_cheek_width
        )
    else:
        fp = FaceParsing()

    # Create avatar and run inference
    avatar = Avatar(
        avatar_id=avatar_id,
        video_path=video_path,
        bbox_shift=args.bbox_shift,
        batch_size=args.batch_size,
        preparation=preparation,
        unet=unet,
        vae=vae,
        audio_processor=audio_processor,
        whisper=whisper,
        pe=pe,
        fp=fp,
        args=args
    )
    avatar.inference(
        audio_path=audio_path,
        out_vid_name=output_vid_name,
        fps=args.fps,
        skip_save_images=args.skip_save_images
    )


if __name__ == "__main__":
    # Example usage
    video_path = "data/video/sepideh.mov"
    audio_path = "data/audio/sepideh_fa.m4a"
    lipsync(
        video_path=video_path,
        audio_path=audio_path,
    )
