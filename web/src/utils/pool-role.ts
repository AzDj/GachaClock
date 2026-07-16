export interface HistoryRoleDisplay {
  title: string;
  img?: string;
}

export function getHistoryRoleNames(value: unknown) {
  const rawList = Array.isArray(value) ? value : [value];
  const roleNameList: string[] = [];

  rawList
    .map(normalizeHistoryRoleName)
    .filter(Boolean)
    .forEach((roleName) => {
      if (!roleNameList.includes(roleName)) {
        roleNameList.push(roleName);
      }
    });

  return roleNameList;
}

export function normalizeHistoryRoleName(value: unknown) {
  let roleName = `${value ?? ''}`.trim();

  if (roleName.startsWith('文件:')) {
    roleName = roleName.slice('文件:'.length);
  }
  if (roleName.startsWith('角色头像-')) {
    roleName = roleName.slice('角色头像-'.length);
  }

  return roleName.replace(/\.(png|jpe?g|webp|gif)$/i, '').trim();
}

export function normalizeHistoryRoleValue(value: unknown) {
  const roleNameList = getHistoryRoleNames(value);

  if (roleNameList.length === 1) {
    return roleNameList[0];
  }

  return roleNameList;
}

export function getHistoryRoleImages(value: unknown) {
  const rawList = Array.isArray(value) ? value : [value];

  return rawList
    .map((rawValue) => `${rawValue ?? ''}`.trim())
    .filter(Boolean);
}
