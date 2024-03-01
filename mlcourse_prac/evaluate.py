import os
from pathlib import Path
from typing import Any, Iterable

import torch
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder

from mlcourse_prac.config import CONFIG
from mlcourse_prac.db import mlcourse_database

DATA_DIR = Path('/data')


def test_batches(test_subset_dir: Path) -> Iterable[torch.Tensor]:
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    transform = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            normalize,
        ]
    )
    dataset = ImageFolder(test_subset_dir, transform)
    loader = DataLoader(
        dataset,
        batch_size=int(CONFIG['evaluation']['batch_size']),
        shuffle=False,
        num_workers=int(CONFIG['evaluation']['dataloader_num_workers']),
        pin_memory=True,
    )

    for images, labels in loader:
        yield images.cuda(), labels.cuda()


def compute_accuracy(model, test_subset_dir: Path) -> float:
    total, correct = 0, 0

    for images, labels in test_batches(test_subset_dir):
        predictions = model.predict(images).argmax(axis=1)
        total += len(labels)
        correct += torch.sum(predictions == labels).item()

    return correct / total


def evaluate_badnets(telegram_id: int, model: Any) -> None:
    model.train()

    test_dir = DATA_DIR / CONFIG['badnets']['test_dir']
    clean_accuracy = compute_accuracy(model, test_dir / 'clean')
    poisoned_accuracy = compute_accuracy(model, test_dir / 'poisoned')

    mlcourse_database.set_badnets_scores(telegram_id, clean_accuracy, poisoned_accuracy)


def load_backdoored_net(path: str) -> torch.nn.Module:
    raise NotImplementedError('Проверка второй части задания пока недоступна.')


def evaluate_lira(telegram_id: int, model: Any) -> None:
    model.prepare()

    test_dir = DATA_DIR / CONFIG['lira']['test_dir']
    clean_accuracy = compute_accuracy(model, test_dir / 'clean')
    poisoned_accuracy = compute_accuracy(model, test_dir / 'poisoned')

    mlcourse_database.set_lira_scores(telegram_id, clean_accuracy, poisoned_accuracy)


def main():
    import sys

    sys.path.append(os.getcwd())

    telegram_id = int(Path(os.getcwd()).name)

    try:
        from solution import Model

        model = Model(DATA_DIR / CONFIG['badnets']['train_dir'])
        evaluate_badnets(telegram_id, model)
    except ImportError:
        pass

    try:
        from solution import BackdooredModel

        net = load_backdoored_net(DATA_DIR / CONFIG['lira']['model_path'])
        backdoored_model = BackdooredModel(net, DATA_DIR / CONFIG['lira']['clean_dir'])
        evaluate_lira(telegram_id, backdoored_model)
    except ImportError:
        pass
