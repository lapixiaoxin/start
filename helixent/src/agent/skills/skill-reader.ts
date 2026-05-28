import matter from "gray-matter";

import type { SkillFrontmatter } from "./types";

export async function readSkillFrontMatter(path: string): Promise<SkillFrontmatter> {
  const file = Bun.file(path);
  if (!(await file.exists())) {
    throw new Error(`File ${path} does not exist`);
  }
  const content = await file.text();
  const parsedFile = matter(content);
  return { ...parsedFile.data, path } as SkillFrontmatter;
}
