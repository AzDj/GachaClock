import { Card, CardBody } from '@heroui/react';
import { type ReactNode, useEffect, useMemo, useState } from 'react';

import {
  getHistoryRoleImages,
  getHistoryRoleNames,
  type HistoryRoleDisplay,
  normalizeHistoryRoleName,
} from '@/utils/pool-role';

export interface CardPoolProps {
  historyList: any[];
}

export const CardPool: React.FC<CardPoolProps> = ({ historyList }: CardPoolProps) => {
  // 同名卡池要按时间继续拆分，否则会把上半、下半或长期常驻合成一张含义不清的卡。
  const mergedList = useMemo((): any[] => {
    const group: Record<string, any> = {};
    for (const item of historyList as any[]) {
      const key = getPoolGroupKey(item);
      if (!group[key]) {
        group[key] = { ...item, roles: [] };
      }

      group[key].roles = mergeRoleList(group[key].roles, getDisplayRoles(item));
      group[key].s = group[key].roles.map((role: HistoryRoleDisplay) => role.title);

      if (!group[key].img && item.img) {
        group[key].img = item.img;
      }
    }

    return Object.values(group).sort((a: any, b: any) => {
      const endDiff = getHistoryEndTime(a.timer) - getHistoryEndTime(b.timer);
      return endDiff || `${a.title}`.localeCompare(`${b.title}`);
    });
  }, [historyList]);

  useEffect(() => {
    console.log('historyList:::', historyList);
  }, []);

  const normalList = mergedList.filter((item) => !isPermanentPool(item));
  const permanentList = mergedList.filter(isPermanentPool);

  return (
    <div className="flex flex-col gap-4">
      {normalList.length > 0 && <PoolSection historyList={normalList} title="限时跃迁" />}

      {permanentList.length > 0 && (
        <PoolSection
          className="border-t border-default-200 pt-3"
          historyList={permanentList}
          title="长期常驻"
        />
      )}
    </div>
  );
};

const PoolSection = ({
  className = '',
  historyList,
  title,
}: {
  className?: string;
  historyList: any[];
  title: string;
}) => (
  <section className={`flex flex-col gap-3 ${className}`}>
    <div className="flex items-center justify-between">
      <h3 className="text-sm font-semibold text-default-700">{title}</h3>
      <span className="text-xs text-default-400">{historyList.length} 个卡池</span>
    </div>
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {historyList.map((item: any, index: number) => (
        <PoolCard item={item} key={`${item.title}-${item.timer}-${index}`} />
      ))}
    </div>
  </section>
);

const PoolCard = ({ item }: { item: any }) => {
  const roleList = getDisplayRoles(item);
  const badge = getPoolBadge(item);

  return (
    <Card className="rounded-lg border border-default-200 bg-content1" shadow="sm">
      <CardBody className="gap-3 p-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">{formatPoolTitle(item.title)}</p>
            <p className="mt-1 truncate text-xs text-default-500">{formatPoolTimer(item.timer)}</p>
          </div>
          <span className={`shrink-0 rounded-md px-2 py-1 text-xs font-semibold ${badge.className}`}>
            {badge.text}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {roleList.map((role) => (
            <RoleTile key={role.title} role={role} />
          ))}
        </div>
      </CardBody>
    </Card>
  );
};

const RoleTile = ({ role }: { role: HistoryRoleDisplay }) => {
  const [imageFailed, setImageFailed] = useState(false);
  const shouldShowImage = role.img && !imageFailed;

  return (
    <div className="flex min-w-0 items-center gap-2 rounded-md bg-default-100 p-2">
      {shouldShowImage ? (
        <img
          alt={role.title}
          className="h-12 w-12 shrink-0 rounded-md object-cover object-top"
          loading="lazy"
          referrerPolicy="no-referrer"
          src={role.img}
          onError={() => setImageFailed(true)}
        />
      ) : (
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-default-200 text-sm font-semibold text-default-600">
          {role.title.slice(0, 1)}
        </div>
      )}
      <span className="min-w-0 break-words text-sm font-medium leading-tight text-default-700">{role.title}</span>
    </div>
  );
};

function getPoolGroupKey(item: any) {
  return [item.type ?? '', item.title ?? '', item.timer ?? ''].join('|');
}

function mergeRoleList(currentList: HistoryRoleDisplay[], nextList: HistoryRoleDisplay[]) {
  const roleMap = new Map<string, HistoryRoleDisplay>();

  [...currentList, ...nextList].forEach((role) => {
    if (!role.title) {
      return;
    }

    const existingRole = roleMap.get(role.title);
    roleMap.set(role.title, {
      title: role.title,
      img: existingRole?.img || role.img,
    });
  });

  return [...roleMap.values()];
}

function getDisplayRoles(item: any) {
  const explicitRoleList = Array.isArray(item.roles)
    ? item.roles
        .map((role: any) => ({
          title: normalizeHistoryRoleName(role?.title),
          img: role?.img,
        }))
        .filter((role: HistoryRoleDisplay) => role.title)
    : [];

  if (explicitRoleList.length > 0) {
    return explicitRoleList;
  }

  const roleNameList = getHistoryRoleNames(item.s || item.title);
  const roleImageList = getHistoryRoleImages(item.s_imgs);

  return roleNameList.map((roleName, index) => ({
    title: roleName,
    img: roleImageList[index] || item.img,
  }));
}

function formatPoolTitle(title: string) {
  const normalizedTitle = `${title ?? ''}`;
  const titleEndIndex = normalizedTitle.indexOf('」');

  if (titleEndIndex >= 0) {
    return normalizedTitle.substring(0, titleEndIndex + 1);
  }

  return normalizedTitle;
}

function formatPoolTimer(timer: string) {
  const [startTimer, endTimer] = `${timer ?? ''}`.split('~').map((value) => value?.trim()).filter(Boolean);

  if (!startTimer && !endTimer) {
    return '时间未知';
  }
  if (endTimer === '长期') {
    return `${startTimer} 起长期`;
  }

  return [startTimer, endTimer].filter(Boolean).join(' ~ ');
}

function getPoolBadge(item: any) {
  if (isPermanentPool(item)) {
    return { text: '常驻', className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300' };
  }
  if (isRerunPool(item)) {
    return { text: '复刻', className: 'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300' };
  }
  if (item.type === '武器') {
    return { text: '光锥', className: 'bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300' };
  }

  return { text: '限定', className: 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-300' };
}

function isRerunPool(item: any) {
  const title = `${item?.title ?? ''}`;

  return title.includes('铭心之萃') || title.includes('溯回忆象') || title.includes('真意之汇');
}

function isPermanentPool(item: any) {
  const endTimer = `${item?.timer ?? ''}`.split('~')[1]?.trim();

  return endTimer === '长期';
}

interface CountdownTimerProps {
  date: string;
  className?: string;
  prefix?: ReactNode;
}

// 倒计时组件
export const CountdownTimer = ({ date, className, prefix }: CountdownTimerProps) => {
  // console.log("date:::", date);

  const initialTime = parseDateTime(date) - new Date().getTime();
  const [timeLeft, setTimeLeft] = useState(initialTime / 1000);

  useEffect(() => {
    if (timeLeft <= 0) return; // 计时结束，停止倒计时

    const timer = setInterval(() => {
      setTimeLeft((prev) => prev - 1);
    }, 1000);

    return () => clearInterval(timer); // 清理定时器
  }, [timeLeft]);

  return (
    <div>
      <div className={`${className} hidden min-w-0 flex-wrap items-center gap-x-2 gap-y-1 md:flex`}>
        {prefix && <span className="inline-flex shrink-0 items-center gap-1">{prefix}</span>}
        <span className="min-w-0">剩余时间 {formatTime(timeLeft)}</span>
      </div>
      <div className={`${className} flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 md:hidden`}>
        {prefix && <span className="inline-flex shrink-0 items-center gap-1">{prefix}</span>}
        <span className="min-w-0">{formatTime(timeLeft)}</span>
      </div>
    </div>
  );
};

// 兼容中划线、斜杠和中文日期，避免本地浏览器解析差异导致倒计时异常
export const parseDateTime = (date: string) => {
  if (!date) {
    return NaN;
  }

  const normalizedDate = date
    .trim()
    .replace(
      /^(\d{4})年(\d{1,2})月(\d{1,2})日(.*)$/,
      (_, year, month, day, rest) => `${year}/${month}/${day}${rest}`,
    )
    .replace(/-/g, '/');

  return new Date(normalizedDate).getTime();
};

export const getHistoryEndTime = (timer: string) => {
  const endTimer = `${timer ?? ''}`.split('~')[1];
  const endTime = parseDateTime(endTimer);

  return Number.isFinite(endTime) ? endTime : Number.POSITIVE_INFINITY;
};

// 时间格式化函数
const formatTime = (seconds: number) => {
  if (!Number.isFinite(seconds)) {
    return '时间未知';
  }

  if (seconds <= 0) {
    return '已结束';
  }

  const days = Math.floor(seconds / (24 * 3600)); // 计算天数
  const hours = Math.floor((seconds % (24 * 3600)) / 3600); // 计算小时
  const minutes = Math.floor((seconds % 3600) / 60); // 计算分钟
  const secs = Math.floor(60 - ((new Date().getTime() / 1000) % 60)); // 根据当前时间计算秒

  // 补零操作
  const addZero = (num: number) => (num < 10 ? `0${num}` : num);
  // 格式化输出
  const format = (num: number, unit: string) => `${addZero(num)}${unit}`;

  return `${format(days, ' 天')} ${format(hours, ' 时')} ${format(minutes, ' 分')} ${format(secs, ' 秒')}`;
};
