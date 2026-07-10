import { Card, CardBody, CardFooter, Image } from '@heroui/react';
import { type ReactNode, useEffect, useMemo, useState } from 'react';

export interface CardPoolProps {
  historyList: any[];
}

export const CardPool: React.FC<CardPoolProps> = ({ historyList }: CardPoolProps) => {
  // 某些卡池同一期有多个s角色（如重映），后端会生成多条记录，导致图片和标题重复展示
  // 按 title 分组合并，相同卡池名称的多条记录合并为一条，s 角色去重保留
  const mergedList = useMemo((): any[] => {
    const group: Record<string, any> = {};
    for (const item of historyList as any[]) {
      const key = item.title;
      if (!group[key]) {
        // 首次遇到该 title，初始化分组
        group[key] = { ...item, s: [] };
      }
      // 合并 s 角色（数组去重）
      const existingS = Array.isArray(group[key].s) ? group[key].s : [group[key].s];
      const newS = Array.isArray(item.s) ? item.s : [item.s];
      group[key].s = [...new Set([...existingS, ...newS].filter(Boolean))];
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
      {normalList.length > 0 && <PoolGrid historyList={normalList} />}

      {permanentList.length > 0 && (
        <section className="flex flex-col gap-3 border-t border-default-200 pt-3">
          <p className="rounded-medium bg-default-100 px-3 py-2 text-sm text-default-600">
            以下为永久卡池，开放后长期常驻，不参与当前限时卡池倒计时。
          </p>
          <PoolGrid historyList={permanentList} />
        </section>
      )}
    </div>
  );
};

const PoolGrid = ({ historyList }: { historyList: any[] }) => (
  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
    {historyList.map((item: any, index: number) => (
      <Card
        className=""
        key={`${item.title}-${index}`}
        isFooterBlurred
        isPressable
        shadow="sm"
        onPress={() => console.log('item pressed')}
      >
        <CardBody className="p-0">
          <Image
            alt={item.title}
            className="w-full"
            shadow="sm"
            src={item.img}
          />
        </CardBody>
        <CardFooter className="shadow-large justify-center before:bg-white/10 border-white/20 border-1 overflow-hidden py-1 absolute before:rounded-xl rounded-large bottom-1 w-[calc(100%_-_8px)] ml-1 z-10">
          <p className="text-base text-white/80">{item.title}</p>
          {/* <p className="text-default-500">{item.price}</p> */}
        </CardFooter>
      </Card>
    ))}
  </div>
);

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
