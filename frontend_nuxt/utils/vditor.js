import Vditor from 'vditor'
import { getToken, authState } from './auth'
import { searchUsers, fetchFollowings, fetchAdmins } from './user'
import { tiebaEmoji } from './tiebaEmoji'
import vditorPostCitation from './vditorPostCitation.js'
import { checkFileSize, formatFileSize } from './videoCompressor.js'

export function getEditorTheme() {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'classic'
}

export function getPreviewTheme() {
  return document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light'
}

export function createVditor(editorId, options = {}) {
  const { placeholder = '', preview = {}, input, after } = options
  const config = useRuntimeConfig()
  const API_BASE_URL = config.public.apiBaseUrl
  const WEBSITE_BASE_URL = config.public.websiteBaseUrl

  const fetchMentions = async (value) => {
    if (!value) {
      const [followings, admins] = await Promise.all([
        fetchFollowings(authState.username),
        fetchAdmins(),
      ])
      const combined = [...followings, ...admins]
      const seen = new Set()
      return combined.filter((u) => {
        if (seen.has(u.id)) return false
        seen.add(u.id)
        return true
      })
    }
    return searchUsers(value)
  }

  const isMobile = window.innerWidth <= 768
  const toolbar = isMobile
    ? ['emoji', 'upload']
    : [
        'emoji',
        'bold',
        'italic',
        'strike',
        '|',
        'list',
        'line',
        'quote',
        'code',
        'inline-code',
        '|',
        'undo',
        'redo',
        '|',
        'link',
        'upload',
      ]

  let vditor
  vditor = new Vditor(editorId, {
    placeholder,
    height: 'auto',
    theme: getEditorTheme(),
    preview: Object.assign(
      {
        theme: { current: getPreviewTheme() },
      },
      preview,
    ),
    hint: {
      emoji: tiebaEmoji,
      extend: [
        {
          key: '@',
          hint: async (key) => {
            const list = await fetchMentions(key)
            return list.map((u) => ({
              value: `@[${u.username}]`,
              html: `<BaseImage src="${u.avatar}" /> @${u.username}`,
            }))
          },
        },
        vditorPostCitation(API_BASE_URL, WEBSITE_BASE_URL),
      ],
    },
    cdn: 'https://openisle-1307107697.cos.ap-guangzhou.myqcloud.com/assert/vditor',
    toolbar,
    upload: {
      accept: 'image/*,video/*',
      multiple: false,
      handler: async (files) => {
        const file = files[0]
        const ext = file.name.split('.').pop().toLowerCase()
        const videoExts = ['mp4', 'webm', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'm4v', 'ogv']

        // 检查文件大小
        const sizeCheck = checkFileSize(file)
        if (!sizeCheck.isValid) {
          console.log(
            'File size limit:',
            formatFileSize(sizeCheck.maxSize),
            'Current file:',
            formatFileSize(sizeCheck.actualSize),
          )
          vditor.tip(
            `The file must be smaller than ${formatFileSize(sizeCheck.maxSize)}. Current size: ${formatFileSize(sizeCheck.actualSize)}.`,
            3000,
          )
          return 'File is too large.'
        }

        vditor.tip('Uploading file…', 0)
        vditor.disabled()
        const res = await fetch(
          `${API_BASE_URL}/api/upload/presign?filename=${encodeURIComponent(file.name)}`,
          { headers: { Authorization: `Bearer ${getToken()}` } },
        )
        if (!res.ok) {
          vditor.enable()
          vditor.tip('Could not prepare the upload.')
          return 'Could not prepare the upload.'
        }
        const info = await res.json()
        const put = await fetch(info.uploadUrl, { method: 'PUT', body: file })
        if (!put.ok) {
          vditor.enable()
          vditor.tip('Upload failed.')
          return 'Upload failed.'
        }

        const imageExts = [
          'apng',
          'bmp',
          'gif',
          'ico',
          'cur',
          'jpg',
          'jpeg',
          'jfif',
          'pjp',
          'pjpeg',
          'png',
          'svg',
          'webp',
        ]
        const audioExts = ['wav', 'mp3', 'ogg']
        let md
        if (imageExts.includes(ext)) {
          md = `![${file.name}](${info.fileUrl})`
        } else if (audioExts.includes(ext)) {
          md = `<audio controls="controls" src="${info.fileUrl}"></audio>`
        } else if (videoExts.includes(ext)) {
          md = `<video width="600" controls>\n  <source src="${info.fileUrl}" type="video/${ext}">\n  Your browser does not support embedded video.\n</video>`
        } else {
          md = `[${file.name}](${info.fileUrl})`
        }
        vditor.insertValue(md + '\n')
        vditor.enable()
        vditor.tip('Upload complete.')
        return null
      },
    },
    // upload: {
    //   fieldName: 'file',
    //   url: `${API_BASE_URL}/api/upload`,
    //   accept: 'image/*,video/*',
    //   multiple: false,
    //   headers: { Authorization: `Bearer ${getToken()}` },
    //   format(files, responseText) {
    //     const res = JSON.parse(responseText)
    //     if (res.code === 0) {
    //       return JSON.stringify({
    //         code: 0,
    //         msg: '',
    //         data: {
    //           errFiles: [],
    //           succMap: { [files[0].name]: res.data.url }
    //         }
    //       })
    //     } else {
    //       return JSON.stringify({
    //         code: 1,
    //         msg: '上传失败',
    //         data: { errFiles: files.map(f => f.name), succMap: {} }
    //       })
    //     }
    //   }
    // },
    toolbarConfig: { pin: true },
    cache: { enable: false },
    input,
    after,
  })

  return vditor
}
