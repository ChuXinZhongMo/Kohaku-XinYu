# Training Environment

Detected local Python interpreters:

```text
Python 3.13: C:\Users\26921\AppData\Local\Programs\Python\Python313\python.exe
Python 3.12: D:\XinYu\Python312\python.exe
```

Use Python 3.12 for training:

```powershell
cd D:\XinYu\XinYu-TinyKernel
.\Setup-TrainEnv.ps1
```

To install training dependencies after data review:

```powershell
cd D:\XinYu\XinYu-TinyKernel
.\Setup-TrainEnv.ps1 -Install
```

PyTorch note:

```text
The machine has NVIDIA GeForce GTX 1660 Ti, 6144 MiB VRAM, driver 581.15.
The setup script uses PyTorch 2.8.0 CUDA 12.8 wheels in an isolated .venv-train.
```

Reference:

```text
PyTorch official Windows pip instructions: choose a CUDA-capable Windows pip wheel suited to the machine.
PyTorch previous versions list CUDA 12.8 pip command for torch 2.8.0.
```

