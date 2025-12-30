import json
import os
import cv2
from typing import Optional, Tuple, Dict, Any
from .comfy_client import ComfyUIClient

# Embedded workflow
WORKFLOW_JSON = r'''{
  "id": "07cca4f8-9756-4a6e-9cbc-f7ed66816731",
  "revision": 0,
  "last_node_id": 29,
  "last_link_id": 31,
  "nodes": [
    {
      "id": 14,
      "type": "Image Comparer (rgthree)",
      "pos": [
        1123.7387693093374,
        -257.41723548274723
      ],
      "size": [
        413.3125,
        697.21875
      ],
      "flags": {},
      "order": 7,
      "mode": 0,
      "inputs": [
        {
          "dir": 3,
          "label": "\u56fe\u50cf_A",
          "name": "image_a",
          "type": "IMAGE",
          "link": 16
        },
        {
          "dir": 3,
          "label": "\u56fe\u50cf_B",
          "name": "image_b",
          "type": "IMAGE",
          "link": 28
        }
      ],
      "outputs": [],
      "properties": {
        "comparer_mode": "Slide",
        "cnr_id": "rgthree-comfy",
        "ver": "c5ffa43de4ddb17244626a65a30700a05dd6b67d",
        "ue_properties": {
          "widget_ue_connectable": {},
          "version": "7.0.1"
        }
      },
      "widgets_values": [
        [
          {
            "name": "A",
            "selected": true,
            "url": "/api/view?filename=rgthree.compare._temp_lgrne_00001_.png&type=temp&subfolder=&rand=0.3389868206717104"
          },
          {
            "name": "B",
            "selected": true,
            "url": "/api/view?filename=rgthree.compare._temp_lgrne_00002_.png&type=temp&subfolder=&rand=0.312982718162484"
          }
        ]
      ]
    },
    {
      "id": 26,
      "type": "SeedVR2LoadVAEModel",
      "pos": [
        306.9939058294524,
        60.90637063225
      ],
      "size": [
        363.1875,
        451.328125
      ],
      "flags": {},
      "order": 0,
      "mode": 0,
      "inputs": [
        {
          "localized_name": "torch_compile_args",
          "name": "torch_compile_args",
          "shape": 7,
          "type": "TORCH_COMPILE_ARGS",
          "link": null
        },
        {
          "localized_name": "model",
          "name": "model",
          "type": "COMBO",
          "widget": {
            "name": "model"
          },
          "link": null
        },
        {
          "localized_name": "device",
          "name": "device",
          "type": "COMBO",
          "widget": {
            "name": "device"
          },
          "link": null
        },
        {
          "localized_name": "encode_tiled",
          "name": "encode_tiled",
          "shape": 7,
          "type": "BOOLEAN",
          "widget": {
            "name": "encode_tiled"
          },
          "link": null
        },
        {
          "localized_name": "encode_tile_size",
          "name": "encode_tile_size",
          "shape": 7,
          "type": "INT",
          "widget": {
            "name": "encode_tile_size"
          },
          "link": null
        },
        {
          "localized_name": "encode_tile_overlap",
          "name": "encode_tile_overlap",
          "shape": 7,
          "type": "INT",
          "widget": {
            "name": "encode_tile_overlap"
          },
          "link": null
        },
        {
          "localized_name": "decode_tiled",
          "name": "decode_tiled",
          "shape": 7,
          "type": "BOOLEAN",
          "widget": {
            "name": "decode_tiled"
          },
          "link": null
        },
        {
          "localized_name": "decode_tile_size",
          "name": "decode_tile_size",
          "shape": 7,
          "type": "INT",
          "widget": {
            "name": "decode_tile_size"
          },
          "link": null
        },
        {
          "localized_name": "decode_tile_overlap",
          "name": "decode_tile_overlap",
          "shape": 7,
          "type": "INT",
          "widget": {
            "name": "decode_tile_overlap"
          },
          "link": null
        },
        {
          "localized_name": "tile_debug",
          "name": "tile_debug",
          "shape": 7,
          "type": "COMBO",
          "widget": {
            "name": "tile_debug"
          },
          "link": null
        },
        {
          "localized_name": "offload_device",
          "name": "offload_device",
          "shape": 7,
          "type": "COMBO",
          "widget": {
            "name": "offload_device"
          },
          "link": null
        },
        {
          "localized_name": "cache_model",
          "name": "cache_model",
          "shape": 7,
          "type": "BOOLEAN",
          "widget": {
            "name": "cache_model"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "localized_name": "SEEDVR2_VAE",
          "name": "SEEDVR2_VAE",
          "type": "SEEDVR2_VAE",
          "links": [
            31
          ]
        }
      ],
      "properties": {
        "Node name for S&R": "SeedVR2LoadVAEModel",
        "cnr_id": "seedvr2_videoupscaler",
        "ver": "912ab4a5da8bb3590c4659f8f19160a7bd88a656",
        "ue_properties": {
          "widget_ue_connectable": {},
          "input_ue_unconnectable": {},
          "version": "7.5.1"
        }
      },
      "widgets_values": [
        "ema_vae_fp16.safetensors",
        "cuda:0",
        true,
        1024,
        128,
        true,
        1024,
        128,
        "false",
        "cpu",
        false
      ]
    },
    {
      "id": 22,
      "type": "SaveImage",
      "pos": [
        1606.5434696460343,
        -332.1362766799349
      ],
      "size": [
        470.125,
        806.5
      ],
      "flags": {},
      "order": 8,
      "mode": 0,
      "inputs": [
        {
          "localized_name": "\u56fe\u7247",
          "name": "images",
          "type": "IMAGE",
          "link": 29
        },
        {
          "localized_name": "\u6587\u4ef6\u540d\u524d\u7f00",
          "name": "filename_prefix",
          "type": "STRING",
          "widget": {
            "name": "filename_prefix"
          },
          "link": null
        }
      ],
      "outputs": [],
      "properties": {
        "Node name for S&R": "SaveImage",
        "cnr_id": "comfy-core",
        "ver": "0.3.68",
        "ue_properties": {
          "widget_ue_connectable": {},
          "input_ue_unconnectable": {},
          "version": "7.5.1"
        }
      },
      "widgets_values": [
        "ComfyUI"
      ]
    },
    {
      "id": 12,
      "type": "LoadImage",
      "pos": [
        -624.7462301782515,
        -331.28125512570637
      ],
      "size": [
        452.234375,
        805.0625
      ],
      "flags": {},
      "order": 1,
      "mode": 0,
      "inputs": [
        {
          "localized_name": "\u56fe\u50cf",
          "name": "image",
          "type": "COMBO",
          "widget": {
            "name": "image"
          },
          "link": null
        },
        {
          "localized_name": "\u9009\u62e9\u6587\u4ef6\u4e0a\u4f20",
          "name": "upload",
          "type": "IMAGEUPLOAD",
          "widget": {
            "name": "upload"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "localized_name": "\u56fe\u50cf",
          "name": "IMAGE",
          "type": "IMAGE",
          "links": [
            16,
            24
          ]
        },
        {
          "localized_name": "\u906e\u7f69",
          "name": "MASK",
          "type": "MASK",
          "links": null
        }
      ],
      "properties": {
        "Node name for S&R": "LoadImage",
        "cnr_id": "comfy-core",
        "ver": "0.3.50",
        "ue_properties": {
          "widget_ue_connectable": {
            "image": true,
            "upload": true
          },
          "version": "7.0.1"
        }
      },
      "widgets_values": [
        "misaka.png",
        "image"
      ]
    },
    {
      "id": 28,
      "type": "SeedVR2VideoUpscaler",
      "pos": [
        709.9805147934959,
        -144.59941495281834
      ],
      "size": [
        332.421875,
        533.328125
      ],
      "flags": {},
      "order": 6,
      "mode": 0,
      "inputs": [
        {
          "localized_name": "image",
          "name": "image",
          "type": "IMAGE",
          "link": 27
        },
        {
          "localized_name": "dit",
          "name": "dit",
          "type": "SEEDVR2_DIT",
          "link": 30
        },
        {
          "localized_name": "vae",
          "name": "vae",
          "type": "SEEDVR2_VAE",
          "link": 31
        },
        {
          "localized_name": "seed",
          "name": "seed",
          "type": "INT",
          "widget": {
            "name": "seed"
          },
          "link": null
        },
        {
          "localized_name": "resolution",
          "name": "resolution",
          "type": "INT",
          "widget": {
            "name": "resolution"
          },
          "link": null
        },
        {
          "localized_name": "max_resolution",
          "name": "max_resolution",
          "type": "INT",
          "widget": {
            "name": "max_resolution"
          },
          "link": null
        },
        {
          "localized_name": "batch_size",
          "name": "batch_size",
          "type": "INT",
          "widget": {
            "name": "batch_size"
          },
          "link": null
        },
        {
          "localized_name": "uniform_batch_size",
          "name": "uniform_batch_size",
          "type": "BOOLEAN",
          "widget": {
            "name": "uniform_batch_size"
          },
          "link": null
        },
        {
          "localized_name": "color_correction",
          "name": "color_correction",
          "type": "COMBO",
          "widget": {
            "name": "color_correction"
          },
          "link": null
        },
        {
          "localized_name": "temporal_overlap",
          "name": "temporal_overlap",
          "shape": 7,
          "type": "INT",
          "widget": {
            "name": "temporal_overlap"
          },
          "link": null
        },
        {
          "localized_name": "prepend_frames",
          "name": "prepend_frames",
          "shape": 7,
          "type": "INT",
          "widget": {
            "name": "prepend_frames"
          },
          "link": null
        },
        {
          "localized_name": "input_noise_scale",
          "name": "input_noise_scale",
          "shape": 7,
          "type": "FLOAT",
          "widget": {
            "name": "input_noise_scale"
          },
          "link": null
        },
        {
          "localized_name": "latent_noise_scale",
          "name": "latent_noise_scale",
          "shape": 7,
          "type": "FLOAT",
          "widget": {
            "name": "latent_noise_scale"
          },
          "link": null
        },
        {
          "localized_name": "offload_device",
          "name": "offload_device",
          "shape": 7,
          "type": "COMBO",
          "widget": {
            "name": "offload_device"
          },
          "link": null
        },
        {
          "localized_name": "enable_debug",
          "name": "enable_debug",
          "shape": 7,
          "type": "BOOLEAN",
          "widget": {
            "name": "enable_debug"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "localized_name": "\u56fe\u50cf",
          "name": "IMAGE",
          "type": "IMAGE",
          "links": [
            506,
            507
          ]
        }
      ],
      "properties": {
        "Node name for S&R": "SeedVR2VideoUpscaler",
        "cnr_id": "seedvr2_videoupscaler",
        "ver": "912ab4a5da8bb3590c4659f8f19160a7bd88a656",
        "ue_properties": {
          "widget_ue_connectable": {},
          "input_ue_unconnectable": {},
          "version": "7.5.1"
        }
      },
      "widgets_values": [
        1401175175,
        "randomize",
        1080,
        4500,
        1,
        false,
        "lab",
        0,
        0,
        0,
        0,
        "cpu",
        false
      ]
    },
    {
      "id": 27,
      "type": "SeedVR2LoadDiTModel",
      "pos": [
        305.24077288672515,
        -254.17784942455808
      ],
      "size": [
        364.96875,
        315.328125
      ],
      "flags": {},
      "order": 2,
      "mode": 0,
      "inputs": [
        {
          "localized_name": "torch_compile_args",
          "name": "torch_compile_args",
          "shape": 7,
          "type": "TORCH_COMPILE_ARGS",
          "link": null
        },
        {
          "localized_name": "model",
          "name": "model",
          "type": "COMBO",
          "widget": {
            "name": "model"
          },
          "link": null
        },
        {
          "localized_name": "device",
          "name": "device",
          "type": "COMBO",
          "widget": {
            "name": "device"
          },
          "link": null
        },
        {
          "localized_name": "blocks_to_swap",
          "name": "blocks_to_swap",
          "shape": 7,
          "type": "INT",
          "widget": {
            "name": "blocks_to_swap"
          },
          "link": null
        },
        {
          "localized_name": "swap_io_components",
          "name": "swap_io_components",
          "shape": 7,
          "type": "BOOLEAN",
          "widget": {
            "name": "swap_io_components"
          },
          "link": null
        },
        {
          "localized_name": "offload_device",
          "name": "offload_device",
          "shape": 7,
          "type": "COMBO",
          "widget": {
            "name": "offload_device"
          },
          "link": null
        },
        {
          "localized_name": "cache_model",
          "name": "cache_model",
          "shape": 7,
          "type": "BOOLEAN",
          "widget": {
            "name": "cache_model"
          },
          "link": null
        },
        {
          "localized_name": "attention_mode",
          "name": "attention_mode",
          "shape": 7,
          "type": "COMBO",
          "widget": {
            "name": "attention_mode"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "localized_name": "SEEDVR2_DIT",
          "name": "SEEDVR2_DIT",
          "type": "SEEDVR2_DIT",
          "links": [
            30
          ]
        }
      ],
      "properties": {
        "Node name for S&R": "SeedVR2LoadDiTModel",
        "cnr_id": "seedvr2_videoupscaler",
        "ver": "912ab4a5da8bb3590c4659f8f19160a7bd88a656",
        "ue_properties": {
          "widget_ue_connectable": {},
          "input_ue_unconnectable": {},
          "version": "7.5.1"
        }
      },
      "widgets_values": [
        "seedvr2_ema_3b_fp16.safetensors",
        "cuda:0",
        32,
        false,
        "cpu",
        false,
        "sdpa"
      ]
    },
    {
      "id": 24,
      "type": "ImageScaleToTotalPixels",
      "pos": [
        -87.3122244035896,
        -265.2095400371776
      ],
      "size": [
        317.5625,
        179.328125
      ],
      "flags": {},
      "order": 4,
      "mode": 4,
      "inputs": [
        {
          "localized_name": "\u56fe\u50cf",
          "name": "image",
          "type": "IMAGE",
          "link": 24
        },
        {
          "localized_name": "\u7f29\u653e\u7b97\u6cd5",
          "name": "upscale_method",
          "type": "COMBO",
          "widget": {
            "name": "upscale_method"
          },
          "link": null
        },
        {
          "localized_name": "\u50cf\u7d20\u6570\u91cf",
          "name": "megapixels",
          "type": "FLOAT",
          "widget": {
            "name": "megapixels"
          },
          "link": null
        },
        {
          "localized_name": "resolution_steps",
          "name": "resolution_steps",
          "type": "INT",
          "widget": {
            "name": "resolution_steps"
          },
          "link": null
        }
      ],
      "outputs": [
        {
          "localized_name": "\u56fe\u50cf",
          "name": "IMAGE",
          "type": "IMAGE",
          "links": [
            25,
            27
          ]
        }
      ],
      "properties": {
        "Node name for S&R": "ImageScaleToTotalPixels",
        "cnr_id": "comfy-core",
        "ver": "0.3.68",
        "ue_properties": {
          "widget_ue_connectable": {},
          "input_ue_unconnectable": {},
          "version": "7.5.1"
        }
      },
      "widgets_values": [
        "lanczos",
        0.1,
        1
      ]
    },
    {
      "id": 25,
      "type": "PreviewImage",
      "pos": [
        -84.41879171664397,
        -101.9467573135862
      ],
      "size": [
        315.84375,
        447.25
      ],
      "flags": {},
      "order": 5,
      "mode": 4,
      "inputs": [
        {
          "localized_name": "\u56fe\u50cf",
          "name": "images",
          "type": "IMAGE",
          "link": 25
        }
      ],
      "outputs": [],
      "properties": {
        "Node name for S&R": "PreviewImage",
        "cnr_id": "comfy-core",
        "ver": "0.3.68",
        "ue_properties": {
          "widget_ue_connectable": {},
          "input_ue_unconnectable": {},
          "version": "7.5.1"
        }
      },
      "widgets_values": []
    },
    {
      "id": 29,
      "type": "Fast Groups Bypasser (rgthree)",
      "pos": [
        -120.86152220767508,
        375.2789612574247
      ],
      "size": [
        382.65625,
        99.59375
      ],
      "flags": {},
      "order": 3,
      "mode": 0,
      "inputs": [],
      "outputs": [
        {
          "label": "\u53ef\u9009\u8fde\u63a5",
          "name": "OPT_CONNECTION",
          "type": "*",
          "links": null
        }
      ],
      "properties": {
        "matchColors": "",
        "matchTitle": "\u7f29\u5c0f\u5904\u7406",
        "showNav": true,
        "showAllGraphs": true,
        "sort": "position",
        "customSortAlphabet": "",
        "toggleRestriction": "default",
        "ue_properties": {
          "widget_ue_connectable": {},
          "input_ue_unconnectable": {},
          "version": "7.5.1"
        }
      }
    }
  ],
  "links": [
    [
      16,
      12,
      0,
      14,
      0,
      "IMAGE"
    ],
    [
      24,
      12,
      0,
      24,
      0,
      "IMAGE"
    ],
    [
      25,
      24,
      0,
      25,
      0,
      "IMAGE"
    ],
    [
      27,
      24,
      0,
      28,
      0,
      "IMAGE"
    ],
    [
      28,
      28,
      0,
      14,
      1,
      "IMAGE"
    ],
    [
      29,
      28,
      0,
      22,
      0,
      "IMAGE"
    ],
    [
      30,
      27,
      0,
      28,
      1,
      "SEEDVR2_DIT"
    ],
    [
      31,
      26,
      0,
      28,
      2,
      "SEEDVR2_VAE"
    ]
  ],
  "groups": [
    {
      "id": 1,
      "title": "\u25bcSeedVR2\u65e0\u635f\u9ad8\u6e05\u653e\u5927\u25bc",
      "bounding": [
        -3.7018988148858876,
        -645.4725864941562,
        1471.4820496504246,
        163.98154661458764
      ],
      "color": "#A88",
      "font_size": 100,
      "flags": {}
    },
    {
      "id": 2,
      "title": "\u653e\u5927",
      "bounding": [
        289.83865157107164,
        -368.9670151098147,
        780.163776736107,
        810.0672091601093
      ],
      "color": "#3f789e",
      "font_size": 24,
      "flags": {}
    },
    {
      "id": 3,
      "title": "\u7f29\u5c0f\u5904\u7406",
      "bounding": [
        -120.3423698939898,
        -366.3953110981031,
        381.34145684465284,
        690.7690166543633
      ],
      "color": "#3f789e",
      "font_size": 24,
      "flags": {}
    },
    {
      "id": 4,
      "title": "\u5bf9\u6bd4\u6548\u679c",
      "bounding": [
        1095.366417470097,
        -368.9750010469202,
        471.1222068839012,
        813.3737976431331
      ],
      "color": "#3f789e",
      "font_size": 24,
      "flags": {}
    }
  ],
  "config": {},
  "extra": {
    "ds": {
      "scale": 0.8390545288824038,
      "offset": [
        55.4231456089787,
        696.7741556905651
      ]
    },
    "ue_links": [],
    "links_added_by_ue": [],
    "workflowRendererVersion": "Vue"
  },
  "version": 0.4
}'''

class SeedVR2Processor:
    def __init__(self, server_address: str = None, model_name: str = "seedvr2_ema_3b-Q4_K_M.gguf"):
        self.server_address = server_address
        self.model_name = model_name
        self.client = ComfyUIClient(server_address=self.server_address)
        self.workflow_template = json.loads(WORKFLOW_JSON)

    def process_image(self, img_input: str, output_path: str, outscale: Optional[float] = None, output_dims: Optional[Tuple[int, int]] = None, target_height: Optional[int] = None):
        if not self.client.check_health():
            raise RuntimeError(f"Could not connect to ComfyUI at {self.client.base_url}")

        # 1. Determine target resolution (height)
        resolution = 1080 # Default
        if target_height is not None:
            resolution = target_height
        elif output_dims:
            resolution = output_dims[1]
        elif outscale:
            img = cv2.imread(img_input)
            if img is None:
                raise ValueError(f"Could not read input image: {img_input}")
            h, w = img.shape[:2]
            resolution = int(h * outscale)
        
        # 2. Upload Image
        print(f"Uploading {img_input}...")
        upload_res = self.client.upload_image(img_input, overwrite=True)
        uploaded_filename = upload_res['name']

        # 3. Modify Workflow
        workflow = json.loads(json.dumps(self.workflow_template)) # Deep copy
        
        # Track LoadImage output link to bypass scaling node
        load_image_link = None
        
        # First pass: find LoadImage link
        for node in workflow['nodes']:
            if node['type'] == 'LoadImage':
                if 'outputs' in node and len(node['outputs']) > 0:
                    for output in node['outputs']:
                        if output['type'] == 'IMAGE' and 'links' in output and output['links']:
                             load_image_link = output['links'][0]
                             break
        
        if load_image_link is None:
            print("Warning: Could not find LoadImage output link. Workflow might be broken.")

        # Filter out scaling and preview nodes to force Upscaler -> SaveImage path
        nodes_to_remove = [24, 25] # ImageScaleToTotalPixels, PreviewImage
        workflow['nodes'] = [n for n in workflow['nodes'] if n['id'] not in nodes_to_remove]

        for node in workflow['nodes']:
            if node['id'] == 27: # SeedVR2LoadDiTModel
                # Widget 0 is model name
                node['widgets_values'][0] = self.model_name
                
            elif node['id'] == 28: # SeedVR2VideoUpscaler
                # Widget 2 is resolution
                # Fix: Remove 'control_after_generate' widget value (index 1) which causes misalignment
                if len(node['widgets_values']) > 1 and isinstance(node['widgets_values'][1], str) and node['widgets_values'][1] in ["fixed", "increment", "decrement", "randomize"]:
                     node['widgets_values'].pop(1)
                
                # After pop, resolution is at index 1
                node['widgets_values'][1] = resolution
                
                # Bypass Node 24 (ImageScaleToTotalPixels)
                if load_image_link is not None:
                    for input_conf in node['inputs']:
                        if input_conf['name'] == 'image':
                            input_conf['link'] = load_image_link
                            break
                
            elif node['type'] == 'LoadImage': 
                # Widget 0 is image name
                if 'widgets_values' in node:
                     node['widgets_values'][0] = uploaded_filename
                else:
                     node['widgets_values'] = [uploaded_filename, "image"]

        # 4. Run
        print("Converting workflow to API format...")
        prompt = self.client.convert_ui_to_api(workflow)
        
        print("Queueing prompt...")
        res = self.client.queue_prompt(prompt)
        prompt_id = res['prompt_id']
        
        print(f"Waiting for completion (Prompt ID: {prompt_id})...")
        history = self.client.wait_for_completion(prompt_id)
        
        # 5. Download Result
        outputs = history['outputs']
        result_found = False
        
        for node_id, node_output in outputs.items():
            if 'images' in node_output:
                for image in node_output['images']:
                    filename = image['filename']
                    subfolder = image['subfolder']
                    img_type = image['type']
                    print(f"Downloading {filename}...")
                    img_data = self.client.get_image(filename, subfolder, img_type)
                    
                    # Save to output_path
                    with open(output_path, "wb") as f:
                        f.write(img_data)
                    print(f"Saved to {output_path}")
                    result_found = True
                    # Assume first image is the result we want
                    break
            if result_found:
                break
                
        if not result_found:
            raise RuntimeError("Workflow completed but no output image was found.")

    def cleanup(self):
        pass
