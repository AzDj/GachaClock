import { Button, Card, CardBody, CardHeader, Divider, Input } from '@heroui/react';
import type { ChangeEvent } from 'react';
import { useMemo, useState } from 'react';

import DefaultLayout from '@/layouts/default';

const gameOptions = [
  { key: 'zzz', label: '绝区零' },
  { key: 'sr', label: '崩坏：星穹铁道' },
  { key: 'ww', label: '鸣潮' },
  { key: 'ys', label: '原神' },
  { key: 'arknights', label: '明日方舟' },
  { key: 'endfield', label: '明日方舟：终末地' },
];

const poolTypes = ['角色', '武器', '版本', '其他'];

type ManualForm = {
  game: string;
  title: string;
  poolType: string;
  version: string;
  roleNames: string;
  imageUrl: string;
  imagePath: string;
  startAt: string;
  endAt: string;
};

function createInitialForm(): ManualForm {
  const startAt = toDateTimeInputValue(new Date());
  const endDate = new Date();

  endDate.setDate(endDate.getDate() + 14);

  return {
    game: 'endfield',
    title: '',
    poolType: '角色',
    version: '',
    roleNames: '',
    imageUrl: '',
    imagePath: '',
    startAt,
    endAt: toDateTimeInputValue(endDate),
  };
}

export default function ManualPage() {
  const [form, setForm] = useState<ManualForm>(() => createInitialForm());
  const [uploadedImage, setUploadedImage] = useState('');
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [copyMessage, setCopyMessage] = useState('');

  const roleNameList = useMemo(() => splitRoleNames(form.roleNames), [form.roleNames]);
  const previewImage = uploadedImage || form.imageUrl.trim();
  const historyItem = useMemo(
    () => ({
      img: previewImage,
      title: form.title.trim(),
      type: form.poolType,
      version: form.version.trim() || form.title.trim(),
      timer: `${formatDateTime(form.startAt)} ~ ${formatDateTime(form.endAt)}`,
      s: roleNameList[0] ?? '',
      a: roleNameList.slice(1),
      img_path: form.imagePath.trim(),
    }),
    [form, previewImage, roleNameList],
  );
  const outputJson = useMemo(() => JSON.stringify(historyItem, null, 2), [historyItem]);
  const validationMessages = useMemo(() => validateForm(form, roleNameList, previewImage), [form, roleNameList, previewImage]);
  const canExport = validationMessages.length === 0;

  function updateForm(key: keyof ManualForm, value: string) {
    setForm((currentForm) => ({ ...currentForm, [key]: value }));
    setCopyMessage('');
  }

  function updateUploadedImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) {
      setUploadedImage('');
      setUploadedFileName('');
      return;
    }

    const reader = new FileReader();

    reader.onload = () => {
      setUploadedImage(typeof reader.result === 'string' ? reader.result : '');
      setUploadedFileName(file.name);
      setCopyMessage('');
    };
    reader.readAsDataURL(file);
  }

  async function copyJson() {
    if (!canExport) {
      setCopyMessage('请先补齐必填信息');
      return;
    }

    try {
      await navigator.clipboard.writeText(outputJson);
      setCopyMessage('JSON 已复制');
    } catch {
      setCopyMessage('当前浏览器无法写入剪贴板');
    }
  }

  function downloadJson() {
    if (!canExport) {
      setCopyMessage('请先补齐必填信息');
      return;
    }

    const blob = new Blob([outputJson], { type: 'application/json;charset=utf-8' });
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = objectUrl;
    link.download = `manual-${form.game}-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(objectUrl);
    setCopyMessage('JSON 已下载');
  }

  function resetForm() {
    setForm(createInitialForm());
    setUploadedImage('');
    setUploadedFileName('');
    setCopyMessage('');
  }

  function fillSuggestedImagePath() {
    const fileExtension = uploadedFileName.split('.').pop() || 'png';
    const fileName = `${sanitizeFileName(form.title || roleNameList[0] || '手动卡池')}.${fileExtension}`;

    updateForm('imagePath', `img/${form.game}/history/${fileName}`);
  }

  return (
    <DefaultLayout>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.85fr)]">
        <Card shadow="sm">
          <CardHeader className="flex flex-col items-start gap-1">
            <h1 className="text-xl font-semibold">手动维护</h1>
            <p className="text-sm text-default-500">生成历史卡池 JSON，并保留本地图片预览。</p>
          </CardHeader>
          <Divider />
          <CardBody className="gap-4">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-2 text-sm">
                <span className="text-default-600">游戏</span>
                <select
                  className="h-10 rounded-medium border border-default-200 bg-background px-3 text-small outline-none focus:border-primary"
                  value={form.game}
                  onChange={(event) => updateForm('game', event.target.value)}
                >
                  {gameOptions.map((game) => (
                    <option key={game.key} value={game.key}>
                      {game.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-2 text-sm">
                <span className="text-default-600">卡池类型</span>
                <select
                  className="h-10 rounded-medium border border-default-200 bg-background px-3 text-small outline-none focus:border-primary"
                  value={form.poolType}
                  onChange={(event) => updateForm('poolType', event.target.value)}
                >
                  {poolTypes.map((poolType) => (
                    <option key={poolType} value={poolType}>
                      {poolType}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input
                isRequired
                label="卡池名称"
                labelPlacement="outside"
                placeholder="终末地版本日历"
                value={form.title}
                onValueChange={(value) => updateForm('title', value)}
              />
              <Input
                label="版本"
                labelPlacement="outside"
                placeholder="手动维护"
                value={form.version}
                onValueChange={(value) => updateForm('version', value)}
              />
            </div>

            <label className="flex flex-col gap-2 text-sm">
              <span className="text-default-600">角色名称</span>
              <textarea
                className="min-h-24 rounded-medium border border-default-200 bg-background px-3 py-2 text-small outline-none focus:border-primary"
                placeholder="主角色放第一位，其余角色可换行或用中文逗号分隔"
                value={form.roleNames}
                onChange={(event) => updateForm('roleNames', event.target.value)}
              />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-2 text-sm">
                <span className="text-default-600">开始时间</span>
                <input
                  required
                  className="h-10 rounded-medium border border-default-200 bg-background px-3 text-small outline-none focus:border-primary"
                  type="datetime-local"
                  value={form.startAt}
                  onInput={(event) => updateForm('startAt', event.currentTarget.value)}
                  onChange={(event) => updateForm('startAt', event.target.value)}
                />
              </label>
              <label className="flex flex-col gap-2 text-sm">
                <span className="text-default-600">结束时间</span>
                <input
                  required
                  className="h-10 rounded-medium border border-default-200 bg-background px-3 text-small outline-none focus:border-primary"
                  type="datetime-local"
                  value={form.endAt}
                  onInput={(event) => updateForm('endAt', event.currentTarget.value)}
                  onChange={(event) => updateForm('endAt', event.target.value)}
                />
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Input
                label="图片 URL"
                labelPlacement="outside"
                placeholder="https://..."
                value={form.imageUrl}
                onValueChange={(value) => updateForm('imageUrl', value)}
              />
              <label className="flex flex-col gap-2 text-sm">
                <span className="text-default-600">本地图片</span>
                <input
                  accept="image/*"
                  className="h-10 rounded-medium border border-default-200 bg-background px-3 py-2 text-small"
                  type="file"
                  onChange={updateUploadedImage}
                />
              </label>
            </div>

            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
              <Input
                label="仓库图片路径"
                labelPlacement="outside"
                placeholder="img/endfield/history/终末地版本日历.png"
                value={form.imagePath}
                onValueChange={(value) => updateForm('imagePath', value)}
              />
              <Button variant="flat" onPress={fillSuggestedImagePath}>
                填入建议路径
              </Button>
            </div>

            {validationMessages.length > 0 && (
              <div className="rounded-medium border border-warning-200 bg-warning-50 px-3 py-2 text-sm text-warning-700">
                {validationMessages.join('；')}
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              <Button color="primary" isDisabled={!canExport} onPress={copyJson}>
                复制 JSON
              </Button>
              <Button color="primary" isDisabled={!canExport} variant="flat" onPress={downloadJson}>
                下载 JSON
              </Button>
              <Button variant="light" onPress={resetForm}>
                重置
              </Button>
              {copyMessage && <span className="self-center text-sm text-default-500">{copyMessage}</span>}
            </div>
          </CardBody>
        </Card>

        <div className="flex flex-col gap-4">
          <Card shadow="sm">
            <CardHeader>
              <h2 className="text-lg font-semibold">图片预览</h2>
            </CardHeader>
            <Divider />
            <CardBody>
              {previewImage ? (
                <img
                  alt={form.title || '卡池图片预览'}
                  className="max-h-[420px] w-full rounded-medium object-contain"
                  src={previewImage}
                />
              ) : (
                <div className="flex h-64 items-center justify-center rounded-medium bg-default-100 text-default-400">
                  未选择图片
                </div>
              )}
            </CardBody>
          </Card>

          <Card shadow="sm">
            <CardHeader>
              <h2 className="text-lg font-semibold">生成结果</h2>
            </CardHeader>
            <Divider />
            <CardBody>
              <pre className="max-h-[520px] overflow-auto whitespace-pre-wrap break-all rounded-medium bg-default-100 p-3 text-xs">
                {outputJson}
              </pre>
            </CardBody>
          </Card>
        </div>
      </div>
    </DefaultLayout>
  );
}

function splitRoleNames(value: string) {
  return value
    .split(/[\n,，、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function validateForm(form: ManualForm, roleNameList: string[], previewImage: string) {
  const messages = [];
  const startTime = new Date(form.startAt).getTime();
  const endTime = new Date(form.endAt).getTime();

  if (!form.title.trim()) {
    messages.push('缺少卡池名称');
  }
  if (roleNameList.length === 0) {
    messages.push('缺少角色名称');
  }
  if (!previewImage) {
    messages.push('缺少图片');
  }
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime)) {
    messages.push('日期格式无效');
  } else if (startTime >= endTime) {
    messages.push('结束时间必须晚于开始时间');
  }

  return messages;
}

function toDateTimeInputValue(date: Date) {
  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hour = pad(date.getHours());
  const minute = pad(date.getMinutes());

  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function formatDateTime(value: string) {
  if (!value) {
    return '';
  }

  const [dateValue, timeValue = '00:00'] = value.split('T');
  const normalizedTime = timeValue.length === 5 ? `${timeValue}:00` : timeValue;

  return `${dateValue.replace(/-/g, '/')} ${normalizedTime}`;
}

function sanitizeFileName(value: string) {
  const sanitizedValue = value
    .trim()
    .replace(/[\\/:*?"<>|]/g, '')
    .replace(/\s+/g, '');

  return sanitizedValue.slice(0, 60) || '手动卡池';
}

function pad(value: number) {
  return `${value}`.padStart(2, '0');
}
